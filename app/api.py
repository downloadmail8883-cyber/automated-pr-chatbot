"""
Data Platform Intake Bot - WITH INTERACTIVE PR CONFLICT HANDLING
User can choose to close existing PR or add to it
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Optional
import os
import traceback
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import sys
from pathlib import Path

app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

try:
    from prompts.system_prompt import SYSTEM_PROMPT, GLUE_DB_FIELDS, S3_BUCKET_FIELDS, IAM_ROLE_FIELDS
    from tools.glue_pr_tool import GlueDBPRInput, create_glue_db_yaml, get_validation_help
    from tools.s3_pr_tool import S3BucketPRInput, create_s3_bucket_yaml, get_s3_validation_help
    from tools.iam_role_tool import IAMRolePRInput, create_iam_role_yaml
    from services.yaml_generator import generate_yaml
    from services.git_ops import (
        create_pull_request,
        close_pull_request,
        add_to_existing_pr,
        get_existing_pr
    )
except ImportError:
    from app.prompts.system_prompt import SYSTEM_PROMPT, GLUE_DB_FIELDS, S3_BUCKET_FIELDS, IAM_ROLE_FIELDS
    from app.tools.glue_pr_tool import GlueDBPRInput, create_glue_db_yaml, get_validation_help
    from app.tools.s3_pr_tool import S3BucketPRInput, create_s3_bucket_yaml, get_s3_validation_help
    from app.tools.iam_role_tool import IAMRolePRInput, create_iam_role_yaml
    from app.services.yaml_generator import generate_yaml
    from app.services.git_ops import (
        create_pull_request,
        close_pull_request,
        add_to_existing_pr,
        get_existing_pr
    )

load_dotenv()

app = FastAPI(title="Data Platform Intake Bot", version="5.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)

# =========================================================
# STATE MACHINE
# =========================================================
class State:
    IDLE = "idle"
    COLLECTING_RESOURCE_TYPE = "collecting_resource_type"
    COLLECTING_DATA = "collecting_data"
    AWAITING_MORE_RESOURCES = "awaiting_more_resources"
    AWAITING_PR_TITLE = "awaiting_pr_title"
    PR_CONFLICT = "pr_conflict"  # NEW STATE
    PR_CREATED = "pr_created"

# =========================================================
# PARSING FUNCTIONS
# =========================================================
def parse_comma_separated(text: str, field_list: List[str]) -> Dict[str, str]:
    values = [v.strip() for v in text.split(",")]
    if len(values) != len(field_list):
        raise ValueError(
            f"Expected {len(field_list)} values but got {len(values)}.\n"
            f"Required fields: {', '.join(field_list)}"
        )
    return dict(zip(field_list, values))

def parse_key_value(text: str) -> Dict[str, str]:
    import yaml
    try:
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            return parsed
    except:
        pass

    result = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    return result

def smart_parse_input(text: str, resource_type: str) -> Dict[str, str]:
    if resource_type == 'glue_db':
        field_list = GLUE_DB_FIELDS
    elif resource_type == 's3_bucket':
        field_list = S3_BUCKET_FIELDS
    elif resource_type == 'iam_role':
        field_list = IAM_ROLE_FIELDS
    else:
        raise ValueError(f"Unknown resource type: {resource_type}")

    if '\n' in text:
        return parse_key_value(text)
    if ':' in text and text.count(':') >= len(field_list) - 1:
        return parse_key_value(text.replace(',', '\n'))

    return parse_comma_separated(text, field_list)

def format_validation_error(error: ValidationError) -> str:
    error_messages = []
    for err in error.errors():
        field = err['loc'][0] if err['loc'] else 'unknown'
        msg = err['msg']
        field_display = field.replace('_', ' ').title()
        error_messages.append(f"**{field_display}**: {msg}")
    return "❌ **Validation Failed**\n\n" + "\n".join(error_messages)

# =========================================================
# PR CREATION WITH CONFLICT DETECTION
# =========================================================
def create_multi_resource_pr(
    glue_dbs: List[Dict],
    s3_buckets: List[Dict],
    iam_roles: List[Dict],
    pr_title: str
) -> Dict[str, str]:
    """
    Create PR with multiple resources
    Returns dict with status and details
    """
    try:
        from git import Repo

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        repo = Repo(repo_root)
        git = repo.git

        # Check for uncommitted changes
        if repo.is_dirty(untracked_files=True):
            untracked = repo.untracked_files
            modified = [item.a_path for item in repo.index.diff(None)]
            all_changes = untracked + modified
            non_intake = [f for f in all_changes if not f.startswith('intake_configs/')]

            if non_intake:
                return {
                    "status": "error",
                    "message": f"Repository has uncommitted changes: {', '.join(non_intake)}"
                }

        git.checkout("dev")
        git.pull("origin", "dev")

        created_files = []

        # Create Glue DB files
        if glue_dbs:
            glue_db_dir = os.path.join(repo_root, "intake_configs", "glue_databases")
            os.makedirs(glue_db_dir, exist_ok=True)

            for glue_data in glue_dbs:
                glue_input = GlueDBPRInput(**glue_data)
                yaml_content = generate_yaml(create_glue_db_yaml(glue_input))
                yaml_path = os.path.join(glue_db_dir, f"{glue_input.database_name}.yaml")

                with open(yaml_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)

                created_files.append(yaml_path)
                print(f"✅ Created: {yaml_path}")

        # Create S3 bucket files
        if s3_buckets:
            s3_bucket_dir = os.path.join(repo_root, "intake_configs", "s3_buckets")
            os.makedirs(s3_bucket_dir, exist_ok=True)

            for s3_data in s3_buckets:
                s3_input = S3BucketPRInput(**s3_data)
                yaml_content = generate_yaml(create_s3_bucket_yaml(s3_input))
                yaml_path = os.path.join(s3_bucket_dir, f"{s3_input.bucket_name}.yaml")

                with open(yaml_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)

                created_files.append(yaml_path)
                print(f"✅ Created: {yaml_path}")

        # Create IAM role files
        if iam_roles:
            iam_role_dir = os.path.join(repo_root, "intake_configs", "iam_roles")
            os.makedirs(iam_role_dir, exist_ok=True)

            for iam_data in iam_roles:
                iam_input = IAMRolePRInput(**iam_data)
                yaml_content = generate_yaml(create_iam_role_yaml(iam_input))
                yaml_path = os.path.join(iam_role_dir, f"{iam_input.role_name}.yaml")

                with open(yaml_path, "w", encoding="utf-8") as f:
                    f.write(yaml_content)

                created_files.append(yaml_path)
                print(f"✅ Created: {yaml_path}")

        # Git operations - commit and push
        repo.index.add(created_files)

        commit_msg = f"{pr_title}\n\n"
        if glue_dbs:
            commit_msg += f"- Added {len(glue_dbs)} Glue Database(s)\n"
        if s3_buckets:
            commit_msg += f"- Added {len(s3_buckets)} S3 Bucket(s)\n"
        if iam_roles:
            commit_msg += f"- Added {len(iam_roles)} IAM Role(s)\n"

        repo.index.commit(commit_msg.strip())
        repo.remote("origin").push("dev")

        print("✅ Changes committed and pushed to fork's dev branch")

        # Try to create PR
        try:
            pr = create_pull_request(
                github_token=os.getenv("GITHUB_TOKEN1"),
                repo_name=os.getenv("REPO_NAME"),
                pr_title=pr_title,
                pr_body=f"## Resources\n\n"
                        f"- {len(glue_dbs)} Glue DB(s)\n"
                        f"- {len(s3_buckets)} S3 Bucket(s)\n"
                        f"- {len(iam_roles)} IAM Role(s)"
            )

            return {
                "status": "success",
                "pr_url": pr['html_url'],
                "pr_number": pr['number']
            }

        except RuntimeError as pr_error:
            error_msg = str(pr_error)

            # Check for PR conflict using special format: "PR_EXISTS:number:url:title"
            if error_msg.startswith("PR_EXISTS:"):
                parts = error_msg.split(":", 3)
                if len(parts) >= 4:
                    pr_number = parts[1]
                    pr_url = parts[2]
                    pr_title_existing = parts[3]

                    return {
                        "status": "pr_exists",
                        "pr_number": pr_number,
                        "pr_url": pr_url,
                        "pr_title": pr_title_existing,
                        "glue_count": len(glue_dbs),
                        "s3_count": len(s3_buckets),
                        "iam_count": len(iam_roles),
                        "message": "A PR already exists. Changes are committed to your fork."
                    }

            return {
                "status": "error",
                "message": error_msg
            }

    except Exception as e:
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }

# =========================================================
# SESSION MANAGEMENT
# =========================================================
session_store = {}

def get_session(sid: str = "default") -> dict:
    if sid not in session_store:
        session_store[sid] = {
            "state": State.IDLE,
            "glue_dbs": [],
            "s3_buckets": [],
            "iam_roles": [],
            "current_resource_type": None,
            "conversation_history": [],
            "pr_conflict_data": None,  # Store PR conflict details
            "pending_pr_title": None   # Store PR title during conflict
        }
    return session_store[sid]

def reset_session(sid: str):
    """Complete session reset"""
    session_store[sid] = {
        "state": State.IDLE,
        "glue_dbs": [],
        "s3_buckets": [],
        "iam_roles": [],
        "current_resource_type": None,
        "conversation_history": [],
        "pr_conflict_data": None,
        "pending_pr_title": None
    }
    print(f"🔄 Session {sid} reset")

# =========================================================
# MODELS
# =========================================================
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str

# =========================================================
# MAIN CHAT ENDPOINT
# =========================================================
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        session = get_session(req.session_id)

        print(f"\n{'='*60}")
        print(f"📨 REQUEST | State: {session['state']}")
        print(f"Resources: {len(session['glue_dbs'])} Glue | {len(session['s3_buckets'])} S3 | {len(session['iam_roles'])} IAM")
        print(f"{'='*60}\n")

        # Welcome message
        if not req.messages:
            return ChatResponse(
                response=(
                    "👋 Hey there! I'm your MIW Data Platform Assistant!\n\n"
                    "I help you create automated Pull Requests for:\n"
                    "✨ **Glue Databases**\n"
                    "✨ **S3 Buckets**\n"
                    "✨ **IAM Roles**\n\n"
                    "What would you like to create today?"
                )
            )

        user_input = req.messages[-1].get("content", "").strip()
        user_lower = user_input.lower()

        # ===== STATE: PR CONFLICT - USER CHOOSING OPTION =====
        if session["state"] == State.PR_CONFLICT:
            conflict_data = session["pr_conflict_data"]

            # Option 1: Add to existing PR
            if any(kw in user_lower for kw in ["add", "existing", "option 1", "1", "keep"]):
                try:
                    # Add comment to existing PR
                    comment = (
                        f"## 🔄 New Resources Added\n\n"
                        f"Additional resources have been added via MIW Data Platform Assistant:\n\n"
                        f"- **{conflict_data['glue_count']} Glue Database(s)**\n"
                        f"- **{conflict_data['s3_count']} S3 Bucket(s)**\n"
                        f"- **{conflict_data['iam_count']} IAM Role(s)**\n\n"
                        f"Please review the latest commits."
                    )

                    add_to_existing_pr(
                        github_token=os.getenv("GITHUB_TOKEN1"),
                        repo_name=os.getenv("REPO_NAME"),
                        pr_number=int(conflict_data['pr_number']),
                        comment=comment
                    )

                    response = (
                        f"✅ **Perfect! Changes added to existing PR!**\n\n"
                        f"📦 **What was added:**\n"
                        f"• {conflict_data['glue_count']} Glue Database(s)\n"
                        f"• {conflict_data['s3_count']} S3 Bucket(s)\n"
                        f"• {conflict_data['iam_count']} IAM Role(s)\n\n"
                        f"🔗 **View PR:** {conflict_data['pr_url']}\n\n"
                        f"Your changes are now in PR #{conflict_data['pr_number']}. "
                        f"I've added a comment to notify the reviewers!\n\n"
                        f"Ready to create more resources? 🚀"
                    )

                    reset_session(req.session_id)
                    return ChatResponse(response=response)

                except Exception as e:
                    response = (
                        f"✅ **Changes are in the existing PR!**\n\n"
                        f"Your resources have been committed and will appear in PR #{conflict_data['pr_number']}.\n\n"
                        f"🔗 {conflict_data['pr_url']}\n\n"
                        f"(Note: Couldn't add comment, but your changes are there!)\n\n"
                        f"Ready for more? 🚀"
                    )
                    reset_session(req.session_id)
                    return ChatResponse(response=response)

            # Option 2: Close existing PR and create new one
            elif any(kw in user_lower for kw in ["close", "new", "option 2", "2", "fresh"]):
                try:
                    # Close the existing PR
                    close_comment = (
                        f"🔒 Closing this PR to create a new one.\n\n"
                        f"A fresh PR will be created with the updated resources."
                    )

                    close_result = close_pull_request(
                        github_token=os.getenv("GITHUB_TOKEN1"),
                        repo_name=os.getenv("REPO_NAME"),
                        pr_number=int(conflict_data['pr_number']),
                        comment=close_comment
                    )

                    print(f"✅ Closed PR #{conflict_data['pr_number']}")

                    # Now create new PR with pending data
                    result = create_multi_resource_pr(
                        glue_dbs=session["glue_dbs"],
                        s3_buckets=session["s3_buckets"],
                        iam_roles=session["iam_roles"],
                        pr_title=session["pending_pr_title"]
                    )

                    if result["status"] == "success":
                        response = (
                            f"🎉 **Success! Old PR closed, new PR created!**\n\n"
                            f"🔒 **Closed:** PR #{conflict_data['pr_number']}\n"
                            f"✨ **New PR:** {result['pr_url']}\n\n"
                            f"📦 **Included:**\n"
                            f"• {len(session['glue_dbs'])} Glue Database(s)\n"
                            f"• {len(session['s3_buckets'])} S3 Bucket(s)\n"
                            f"• {len(session['iam_roles'])} IAM Role(s)\n\n"
                            f"Your fresh PR is ready for review! Want to create more? 🚀"
                        )
                        reset_session(req.session_id)
                        return ChatResponse(response=response)
                    else:
                        response = f"❌ Closed old PR but failed to create new one: {result.get('message', 'Unknown error')}"
                        reset_session(req.session_id)
                        return ChatResponse(response=response)

                except Exception as e:
                    traceback.print_exc()
                    response = f"❌ Failed to close PR: {str(e)}\n\nTry closing it manually on GitHub."
                    reset_session(req.session_id)
                    return ChatResponse(response=response)

            else:
                # Invalid choice
                return ChatResponse(
                    response=(
                        "Please choose an option:\n\n"
                        "**Option 1:** Type **'add to existing'** or **'1'**\n"
                        "→ Your changes will be added to the current PR\n\n"
                        "**Option 2:** Type **'close and create new'** or **'2'**\n"
                        "→ I'll close the old PR and create a fresh one"
                    )
                )

        # ===== STATE: AWAITING PR TITLE =====
        if session["state"] == State.AWAITING_PR_TITLE:
            if len(user_input.split()) >= 3:
                result = create_multi_resource_pr(
                    glue_dbs=session["glue_dbs"],
                    s3_buckets=session["s3_buckets"],
                    iam_roles=session["iam_roles"],
                    pr_title=user_input
                )

                # Handle SUCCESS
                if result["status"] == "success":
                    response = (
                        f"🎉 **SUCCESS!** Your PR is live!\n\n"
                        f"📋 **Title:** {user_input}\n"
                        f"🔗 **PR Link:** {result['pr_url']}\n"
                        f"📦 **Included:** {len(session['glue_dbs'])} Glue DB(s), "
                        f"{len(session['s3_buckets'])} S3 Bucket(s), {len(session['iam_roles'])} IAM Role(s)\n\n"
                        f"✅ Session reset! Want to create another PR?"
                    )
                    reset_session(req.session_id)
                    return ChatResponse(response=response)

                # Handle PR CONFLICT
                elif result["status"] == "pr_exists":
                    # Store conflict data in session
                    session["pr_conflict_data"] = result
                    session["pending_pr_title"] = user_input
                    session["state"] = State.PR_CONFLICT

                    response = (
                        f"⚠️ **Hold on! A PR already exists!**\n\n"
                        f"📋 **Existing PR:** {result.get('pr_title', 'Unknown')}\n"
                        f"🔗 **URL:** {result['pr_url']}\n"
                        f"🔢 **Number:** #{result['pr_number']}\n\n"
                        f"✅ **Good news:** Your changes are already committed and pushed!\n\n"
                        f"📦 **What's ready to add:**\n"
                        f"• {result['glue_count']} Glue Database(s)\n"
                        f"• {result['s3_count']} S3 Bucket(s)\n"
                        f"• {result['iam_count']} IAM Role(s)\n\n"
                        f"**What would you like to do?**\n\n"
                        f"**Option 1:** Type **'add to existing'** or **'1'**\n"
                        f"→ Add your new resources to the existing PR #{result['pr_number']}\n\n"
                        f"**Option 2:** Type **'close and create new'** or **'2'**\n"
                        f"→ Close PR #{result['pr_number']} and create a fresh PR with your resources\n\n"
                        f"Choose wisely! 🤔"
                    )
                    return ChatResponse(response=response)

                # Handle ERROR
                else:
                    error_response = f"❌ Error: {result['message']}\n\n🔄 Session reset. Try again?"
                    reset_session(req.session_id)
                    return ChatResponse(response=error_response)
            else:
                return ChatResponse(
                    response="Please provide a descriptive PR title (at least 3 words).\nExample: 'Add sales analytics resources for LATAM'"
                )

        # ===== DETECT DATA INPUT =====
        has_separators = (',' in user_input or (':' in user_input and '\n' in user_input))
        is_substantial = len(user_input) > 40
        is_not_question = not any(q in user_lower for q in ['what', 'how', 'which', 'prefer', '?', 'format'])

        if has_separators and is_substantial and is_not_question and session.get("current_resource_type"):
            resource_type = session["current_resource_type"]

            try:
                parsed = smart_parse_input(user_input, resource_type)

                if resource_type == "glue_db":
                    glue = GlueDBPRInput(**parsed)
                    session["glue_dbs"].append(glue.dict())
                    name = glue.database_name
                    resource_name = "Glue Database"
                elif resource_type == "s3_bucket":
                    s3 = S3BucketPRInput(**parsed)
                    session["s3_buckets"].append(s3.dict())
                    name = s3.bucket_name
                    resource_name = "S3 Bucket"
                elif resource_type == "iam_role":
                    iam = IAMRolePRInput(**parsed)
                    session["iam_roles"].append(iam.dict())
                    name = iam.role_name
                    resource_name = "IAM Role"

                session["current_resource_type"] = None
                session["state"] = State.AWAITING_MORE_RESOURCES

                return ChatResponse(
                    response=(
                        f"✅ Perfect! I've got your {resource_name} '{name}'.\n\n"
                        f"Want to add more resources to this PR?\n"
                        f"• Another Glue Database\n"
                        f"• An S3 Bucket\n"
                        f"• An IAM Role\n\n"
                        f"Or type **'done'** to create the PR! 🚀"
                    )
                )

            except ValidationError as ve:
                error_msg = format_validation_error(ve)
                if resource_type == "glue_db":
                    error_msg += "\n\n💡 Type 'validation help' to see all requirements."
                return ChatResponse(response=error_msg)

            except Exception as e:
                return ChatResponse(response=f"❌ Validation error: {str(e)}\n\nPlease check your input.")

        # ===== DETECT DONE =====
        if any(kw in user_lower for kw in ["done", "create pr", "finish"]) or ("no" in user_lower and "more" in user_lower):
            total = len(session["glue_dbs"]) + len(session["s3_buckets"]) + len(session["iam_roles"])

            if total == 0:
                return ChatResponse(
                    response="We haven't collected any resources yet! What would you like to create?"
                )

            session["state"] = State.AWAITING_PR_TITLE
            return ChatResponse(
                response=(
                    f"Awesome! Here's what we're packaging:\n"
                    f"📦 {len(session['glue_dbs'])} Glue DB(s)\n"
                    f"📦 {len(session['s3_buckets'])} S3 Bucket(s)\n"
                    f"📦 {len(session['iam_roles'])} IAM Role(s)\n\n"
                    f"What should the PR title be?\n"
                    f"(Example: 'Add sales analytics resources for LATAM')"
                )
            )

        # ===== LLM CONVERSATION =====
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    "CRITICAL RULES:\n"
                    "1. NEVER generate fake PR links\n"
                    "2. NEVER say 'PR created' - you CANNOT create PRs\n"
                    "3. ONLY collect information\n"
                    "4. The BACKEND creates PRs, not you"
                )
            }
        ]
        messages.extend(req.messages)

        llm_response = llm.invoke(messages)

        # Track resource type
        resp_lower = llm_response.content.lower()
        if "glue" in resp_lower and ("database" in resp_lower or "db" in resp_lower):
            session["current_resource_type"] = "glue_db"
            session["state"] = State.COLLECTING_DATA
        elif "s3" in resp_lower and "bucket" in resp_lower:
            session["current_resource_type"] = "s3_bucket"
            session["state"] = State.COLLECTING_DATA
        elif "iam" in resp_lower and "role" in resp_lower:
            session["current_resource_type"] = "iam_role"
            session["state"] = State.COLLECTING_DATA

        return ChatResponse(response=llm_response.content)

    except Exception as e:
        traceback.print_exc()
        return ChatResponse(response=f"❌ System Error: {str(e)}")

# =========================================================
# UTILITY ENDPOINTS
# =========================================================
@app.get("/")
def root():
    return {"status": "online", "version": "5.1.0", "service": "Data Platform Intake Bot"}

@app.post("/reset")
def reset(session_id: str = "default"):
    reset_session(session_id)
    return {"status": "reset", "message": "Session cleared successfully"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "github": bool(os.getenv("GITHUB_TOKEN1")),
        "username": bool(os.getenv("GITHUB_USERNAME"))
    }

@app.get("/session/{session_id}")
def get_session_info(session_id: str = "default"):
    """Debug endpoint to check session state"""
    session = get_session(session_id)
    return {
        "session_id": session_id,
        "state": session["state"],
        "resources": {
            "glue_dbs": len(session["glue_dbs"]),
            "s3_buckets": len(session["s3_buckets"]),
            "iam_roles": len(session["iam_roles"])
        },
        "current_resource_type": session["current_resource_type"],
        "has_pr_conflict": session["pr_conflict_data"] is not None
    }