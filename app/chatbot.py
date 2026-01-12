import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant",
    temperature=0.4
)

REQUIRED_FIELDS = [
    "intake_id",
    "database_name",
    "database_s3_location",
    "database_description",
    "aws_account_id",
    "region",
    "data_construct",
    "data_env",
    "data_layer",
    "source_name",
    "enterprise_or_func_name",
    "enterprise_or_func_subgrp_name",
    "data_owner_email",
    "data_owner_github_uname",
    "data_leader",
]

FIELD_QUESTIONS = {
    "intake_id": "What’s the intake ID?",
    "database_name": "What should we name the Glue database?",
    "database_s3_location": "Where should the data live in S3?",
    "database_description": "Short description of this database?",
    "aws_account_id": "Which AWS account ID?",
    "region": "Which AWS region?",
    "data_construct": "Is this Source or Consumer?",
    "data_env": "Which environment? (dev / qa / prd)",
    "data_layer": "Which data layer?",
    "source_name": "What’s the source system name?",
    "enterprise_or_func_name": "Enterprise or functional group name?",
    "enterprise_or_func_subgrp_name": "Sub-group name?",
    "data_owner_email": "Data owner email?",
    "data_owner_github_uname": "Data owner GitHub username?",
    "data_leader": "Who is the data leader?",
}

# -------------------------------
# STATE (SIMPLE & SAFE)
# -------------------------------
state = {
    "active": False,
    "current_index": 0,
    "data": {},
    "ready": False,
}

# -------------------------------
# HELPERS
# -------------------------------
def is_glue_intent(text: str) -> bool:
    text = text.replace(" ", "")
    return any(x in text for x in ["glue", "gluedb", "gludb", "gluedatabase"])

def is_create_intent(text: str) -> bool:
    return text in {"create", "yes", "yes please", "proceed", "go ahead"}

# -------------------------------
# MAIN ENTRY
# -------------------------------
def ask_groq(user_input: str):
    text = user_input.lower().strip()

    # ---- SUPPORTED PRs ----
    if "pr" in text and "support" in text:
        return {
            "type": "message",
            "content": (
                "I can help you with:\n\n"
                "✅ Glue Database PRs\n"
                "🚧 IAM PRs (coming soon)\n"
                "🚧 Resource Policy PRs (coming soon)\n\n"
                "Just say **create glue db** to begin 🚀"
            )
        }

    # ---- START GLUE FLOW ----
    if is_glue_intent(text) and not state["active"]:
        state["active"] = True
        state["current_index"] = 0
        state["data"] = {}
        state["ready"] = False

        field = REQUIRED_FIELDS[0]
        return {
            "type": "message",
            "content": f"Awesome 👍 Let’s create a Glue Database.\n\n{FIELD_QUESTIONS[field]}"
        }

    # ---- COLLECT DATA ----
    if state["active"] and not state["ready"]:
        field = REQUIRED_FIELDS[state["current_index"]]
        state["data"][field] = user_input.strip()
        state["current_index"] += 1

        if state["current_index"] < len(REQUIRED_FIELDS):
            next_field = REQUIRED_FIELDS[state["current_index"]]
            return {
                "type": "message",
                "content": FIELD_QUESTIONS[next_field]
            }
        else:
            state["ready"] = True
            return {
                "type": "message",
                "content": (
                    "Nice 👍 I’ve captured all required details.\n\n"
                    "Type **create** to generate the YAML and raise the PR 🚀"
                )
            }

    # ---- CREATE PR ----
    if state["ready"] and is_create_intent(text):
        payload = state["data"]

        # RESET STATE CLEANLY
        state["active"] = False
        state["ready"] = False
        state["current_index"] = 0
        state["data"] = {}

        return {
            "type": "action",
            "action": "create_pr",
            "data": payload
        }

    # ---- INVALID CREATE ----
    if is_create_intent(text) and not state["ready"]:
        return {
            "type": "message",
            "content": "⚠️ I need to collect all details first. Start with **create glue db** 🙂"
        }

    # ---- FALLBACK ----
    return {
        "type": "message",
        "content": "🙂 I didn’t quite get that. You can say **create glue db** to begin."
    }
