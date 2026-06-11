"""
Data Platform Intake Bot - Main API
With comprehensive validation layer
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Optional
import os
import traceback
from dotenv import load_dotenv

# Import from local modules
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
    from services.git_ops import create_pull_request
    from llm.groq_client import get_llm, is_groq_configured
    from services.terraform_glue_chatbot import (
        TERRAFORM_CONTEXT,
        reset_terraform_session,
        run_terraform_chat_turn,
        terraform_ai_enabled,
    )
except ImportError:
    from app.prompts.system_prompt import SYSTEM_PROMPT, GLUE_DB_FIELDS, S3_BUCKET_FIELDS, IAM_ROLE_FIELDS
    from app.tools.glue_pr_tool import GlueDBPRInput, create_glue_db_yaml, get_validation_help
    from app.tools.s3_pr_tool import S3BucketPRInput, create_s3_bucket_yaml, get_s3_validation_help
    from app.tools.iam_role_tool import IAMRolePRInput, create_iam_role_yaml
    from app.services.yaml_generator import generate_yaml
    from app.services.git_ops import create_pull_request
    from app.llm.groq_client import get_llm, is_groq_configured
    from app.services.terraform_glue_chatbot import (
        TERRAFORM_CONTEXT,
        reset_terraform_session,
        run_terraform_chat_turn,
        terraform_ai_enabled,
    )

load_dotenv()

app = FastAPI(title="Data Platform Intake Bot", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = get_llm()

# =========================================================
# Parsing Functions
# =========================================================
def parse_comma_separated(text: str, field_list: List[str]) -> Dict[str, str]:
    values = [v.strip() for v in text.split(",")]
    if len(values) != len(field_list):
        raise ValueError(
            f"Expected {len(field_list)} values but got {len(values)}.\n\n"
            f"Required: {', '.join(field_list)}"
        )
    return dict(zip(field_list, values))


def parse_key_value(text: str) -> Dict[str, str]:
    """Parse key-value format with basic YAML support"""
    import yaml

    # Try YAML parsing first
    try:
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            return parsed
    except:
        pass

    # Fallback to line-by-line parsing
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
    """Format Pydantic validation errors in a user-friendly way"""
    error_messages = []

    for err in error.errors():
        field = err['loc'][0] if err['loc'] else 'unknown'
        msg = err['msg']

        # Make field names more readable
        field_display = field.replace('_', ' ').title()

        error_messages.append(f"**{field_display}**: {msg}")

    return "❌ **Validation Failed**\n\n" + "\n".join(error_messages)


def deterministic_chat_response(user_input: str, session: Dict) -> Optional[str]:
    user_lower = user_input.lower().strip()

    if not user_lower or user_lower in {"hi", "hello", "hey", "start"}:
        return (
            "👋 Hi! I'm your Intake Automation PR Bot.\n\n"
            "I can help you create automated pull requests for:\n"
            "• Glue Databases\n"
            "• S3 Buckets\n"
            "• IAM Roles\n\n"
            "Tell me which resource you want to create, and I'll guide you through the required fields."
        )

    if "glue" in user_lower and ("database" in user_lower or "db" in user_lower or "create" in user_lower):
        session["current_resource_type"] = "glue_db"
        session["state"] = "collecting_data"
        return (
            "Let's create a Glue Database. Provide the 15 required fields in one of these formats:\n\n"
            "Comma-separated:\n"
            f"{', '.join(GLUE_DB_FIELDS)}\n\n"
            "Key-value:\n"
            + "\n".join(f"{field}:" for field in GLUE_DB_FIELDS)
        )

    if "s3" in user_lower and ("bucket" in user_lower or "create" in user_lower):
        session["current_resource_type"] = "s3_bucket"
        session["state"] = "collecting_data"
        return (
            "Let's create an S3 Bucket. Provide the 7 required fields in one of these formats:\n\n"
            "Comma-separated:\n"
            f"{', '.join(S3_BUCKET_FIELDS)}\n\n"
            "Key-value:\n"
            + "\n".join(f"{field}:" for field in S3_BUCKET_FIELDS)
        )

    if "iam" in user_lower and ("role" in user_lower or "create" in user_lower):
        session["current_resource_type"] = "iam_role"
        session["state"] = "collecting_data"
        return (
            "Let's create an IAM Role. IAM roles must use key-value format. Provide these fields:\n\n"
            + "\n".join(f"{field}:" for field in IAM_ROLE_FIELDS)
        )

    if any(keyword in user_lower for keyword in ["glue", "s3", "iam", "role", "bucket", "database"]):
        return (
            "I can help with Glue Databases, S3 Buckets, or IAM Roles. "
            "Say which one you want to create, for example: 'create a Glue database'."
        )

    return (
        "I can guide you through creating a Glue Database, S3 Bucket, or IAM Role. "
        "Tell me which resource you want to create to get started."
    )


# =========================================================
# PR Creation - Supports Glue DB, S3, and IAM
# =========================================================
def create_multi_resource_pr(
    glue_dbs: List[Dict],
    s3_buckets: List[Dict],
    iam_roles: List[Dict],
    pr_title: str
) -> str:
    try:
        from git import Repo

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        repo = Repo(repo_root)
        git = repo.git

        if repo.is_dirty(untracked_files=True):
            untracked = repo.untracked_files
            modified = [item.a_path for item in repo.index.diff(None)]
            all_changes = untracked + modified
            non_intake = [f for f in all_changes if not f.startswith('intake_configs/')]

            if non_intake:
                raise RuntimeError(
                    f"Repository has uncommitted changes: {', '.join(non_intake)}\n"
                    "Please commit or stash them first."
                )

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
                print(f"✅ Created Glue DB YAML: {yaml_path}")

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
                print(f"✅ Created S3 Bucket YAML: {yaml_path}")

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
                print(f"✅ Created IAM Role YAML: {yaml_path}")

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

        try:
            pr = create_pull_request(
                github_token=os.getenv("GITHUB_TOKEN1"),
                repo_name=os.getenv("REPO_NAME"),
                pr_title=pr_title,
                pr_body=f"## Resources\n\n"
                        f"{f'- {len(glue_dbs)} Glue DB(s)' if glue_dbs else ''}\n"
                        f"{f'- {len(s3_buckets)} S3 Bucket(s)' if s3_buckets else ''}\n"
                        f"{f'- {len(iam_roles)} IAM Role(s)' if iam_roles else ''}"
            )

            return (
                f"🎉 Boom! Your PR is live!\n\n"
                f"📋 **Title:** {pr_title}\n"
                f"📦 **What's included:** {len(glue_dbs)} Glue DB(s), {len(s3_buckets)} S3 Bucket(s), {len(iam_roles)} IAM Role(s)\n"
                f"🔗 **View it here:** {pr['html_url']}\n\n"
                f"Great work! Your team can review it whenever they're ready. Need anything else? 😊"
            )

        except RuntimeError as pr_error:
            if "already exists" in str(pr_error).lower():
                return (
                    "🤔 Hmm, looks like you already have a PR open from your fork to upstream!\n\n"
                    "**No worries though!** Your new changes are already committed to your fork's dev branch. "
                    "Here are your options:\n\n"
                    "1️⃣ **Keep the existing PR** - It'll automatically update with your new resources (easiest option!)\n"
                    "2️⃣ **Close the old PR and start fresh** - Let me know and I'll create a brand new one\n\n"
                    "What would you like to do?"
                )
            raise pr_error

    except Exception as e:
        traceback.print_exc()
        return f"❌ Failed: {str(e)}"


# =========================================================
# Session
# =========================================================
session_store = {}

def get_session(sid: str = "default") -> dict:
    if sid not in session_store:
        session_store[sid] = {
            "glue_dbs": [],
            "s3_buckets": [],
            "iam_roles": [],
            "current_resource_type": None,
            "awaiting_pr_title": False,
            "state": "idle"
        }
    return session_store[sid]


# =========================================================
# Models
# =========================================================
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str


class TerraformChatRequest(BaseModel):
    message: Optional[str] = None
    session_id: Optional[str] = "default"


class TerraformChatResponse(BaseModel):
    response: str
    completed: bool = False
    terraform_output: Optional[str] = None
    output_path: Optional[str] = None
    collected_fields: Dict[str, str] = {}
    context: str
    ai_enabled: bool = False


# =========================================================
# Routes
# =========================================================
@app.get("/")
def root():
    return {"status": "online", "service": "Data Platform Intake Bot", "version": "4.0.0"}


@app.get("/terraform/context")
def terraform_context():
    return {"context": TERRAFORM_CONTEXT, "ai_enabled": terraform_ai_enabled()}


@app.post("/terraform/chat", response_model=TerraformChatResponse)
def terraform_chat(req: TerraformChatRequest):
    result = run_terraform_chat_turn(req.session_id or "default", req.message)
    return TerraformChatResponse(
        response=result["response"],
        completed=result["completed"],
        terraform_output=result["terraform_output"],
        output_path=result["output_path"],
        collected_fields={key: str(value) for key, value in result["answers"].items()},
        context=result["context"],
        ai_enabled=result["ai_enabled"],
    )


@app.post("/terraform/reset")
def terraform_reset(session_id: str = "default"):
    reset_terraform_session(session_id)
    return {"status": "reset", "session_id": session_id}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        session = get_session(req.session_id)

        print(f"\n{'='*60}")
        print(f"📨 INCOMING REQUEST")
        print(f"Session ID: {req.session_id}")
        print(f"User input: {req.messages[-1].get('content', '') if req.messages else 'None'}")
        print(f"Session state: awaiting_pr_title={session.get('awaiting_pr_title')}")
        print(f"Resources collected: {len(session.get('glue_dbs', []))} Glue, {len(session.get('s3_buckets', []))} S3, {len(session.get('iam_roles', []))} IAM")
        print(f"Current resource type: {session.get('current_resource_type')}")
        print(f"{'='*60}\n")

        if not req.messages:
            return ChatResponse(
                response=(
                    "👋 Hey there! I'm your MIW Data Platform Assistant!\n\n"
                    "I'm here to help you create automated Pull Requests for:\n"
                    "✨ **Glue Databases**\n"
                    "✨ **S3 Buckets**\n"
                    "✨ **IAM Roles**\n\n"
                    "No more manual YAML editing or Git gymnastics - just chat with me and I'll handle all the technical stuff! 🚀\n\n"
                    "So, what are we building today?"
                )
            )

        user_input = req.messages[-1].get("content", "").strip()
        user_lower = user_input.lower()

        # Show validation help if requested
        if "validation" in user_lower and "help" in user_lower:
            return ChatResponse(response=get_validation_help())

        # State: Awaiting PR title
        if session.get("awaiting_pr_title"):
            # User must provide an actual title (more than 2 words)
            if len(user_input.split()) >= 3:
                result = create_multi_resource_pr(
                    glue_dbs=session["glue_dbs"],
                    s3_buckets=session["s3_buckets"],
                    iam_roles=session["iam_roles"],
                    pr_title=user_input
                )
                session_store[req.session_id] = get_session("new")
                return ChatResponse(response=result)
            else:
                return ChatResponse(
                    response="Please provide a descriptive PR title (at least 3 words). For example: 'Add sales analytics Glue database for LATAM'"
                )

        # State: Collecting data
        has_separators = (',' in user_input or (':' in user_input and '\n' in user_input))
        is_substantial = len(user_input) > 40
        is_not_question = not any(q in user_lower for q in ['what', 'how', 'which', 'prefer', '?', 'format', 'option'])

        if has_separators and is_substantial and is_not_question:
            resource_type = session.get("current_resource_type")

            if resource_type:
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
                    session["state"] = "confirming"

                    return ChatResponse(
                        response=(
                            f"✅ Perfect! I've got all the details for your {resource_name} '{name}'.\n\n"
                            f"Want to add more resources to this PR? You can add:\n"
                            f"• Another Glue Database\n"
                            f"• An S3 Bucket\n"
                            f"• An IAM Role\n\n"
                            f"Or just type **'done'** if you're ready to create the PR! 🚀"
                        )
                    )

                except ValidationError as ve:
                    # Format Pydantic validation errors nicely
                    error_msg = format_validation_error(ve)

                    # Add validation help for Glue DB errors
                    if resource_type == "glue_db":
                        error_msg += "\n\n💡 **Need help with validation rules?** Type 'validation help' to see all requirements."

                    return ChatResponse(response=error_msg)

                except Exception as e:
                    error_msg = str(e)
                    print(f"\n❌ ERROR: {error_msg}")
                    traceback.print_exc()

                    return ChatResponse(
                        response=f"❌ Validation error: {error_msg}\n\nPlease check your input and try again."
                    )

        # State: User done collecting
        if any(keyword in user_lower for keyword in ["done", "create pr", "make pr", "generate pr", "finish"]) or ("no" in user_lower and "more" in user_lower):
            total_resources = len(session["glue_dbs"]) + len(session["s3_buckets"]) + len(session["iam_roles"])

            if total_resources == 0:
                return ChatResponse(
                    response="Hmm, we haven't collected any resources yet! Would you like to add a Glue Database, S3 Bucket, or IAM Role? 🤔"
                )

            session["awaiting_pr_title"] = True
            return ChatResponse(
                response=(
                    f"Awesome! Here's what we're packaging up:\n"
                    f"📦 {len(session['glue_dbs'])} Glue Database(s)\n"
                    f"📦 {len(session['s3_buckets'])} S3 Bucket(s)\n"
                    f"📦 {len(session['iam_roles'])} IAM Role(s)\n\n"
                    f"Now, let's give this PR a good title! What should we call it?\n"
                    f"(Something descriptive like 'Add sales analytics Glue database for LATAM')"
                )
            )

        # LLM conversation
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    "ABSOLUTE RULE: You are NOT allowed to generate, invent, create, or make up ANY data values. "
                    "If the user has not provided actual field values yet, you MUST ask them to provide the values. "
                    "DO NOT show example values. DO NOT pretend you received data. "
                    "ONLY confirm data collection AFTER the user has provided actual values."
                )
            }
        ]
        messages.extend(req.messages)

        if llm is None:
            fallback_response = deterministic_chat_response(user_input, session)
            return ChatResponse(
                response=fallback_response
            )

        llm_response = llm.invoke(messages)

        # Track resource type
        resp_lower = llm_response.content.lower()
        if "glue" in resp_lower and ("database" in resp_lower or "db" in resp_lower):
            session["current_resource_type"] = "glue_db"
            session["state"] = "collecting_data"
        elif "s3" in resp_lower and "bucket" in resp_lower:
            session["current_resource_type"] = "s3_bucket"
            session["state"] = "collecting_data"
        elif "iam" in resp_lower and "role" in resp_lower:
            session["current_resource_type"] = "iam_role"
            session["state"] = "collecting_data"

        return ChatResponse(response=llm_response.content)

    except Exception as e:
        traceback.print_exc()
        return ChatResponse(response=f"❌ Error: {str(e)}")


@app.post("/reset")
def reset(session_id: str = "default"):
    if session_id in session_store:
        del session_store[session_id]
    return {"status": "reset"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "groq": is_groq_configured(),
        "github": bool(os.getenv("GITHUB_TOKEN1")),
        "username": bool(os.getenv("GITHUB_USERNAME")),
    }