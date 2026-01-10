"""
Conversational Chatbot for Data Platform Intake

ONLY supported PR:
- Glue Database PR ✅

Other PRs:
- IAM 🚧
- Resource Policy 🚧
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0
)

SYSTEM_PROMPT = """
You are a professional Data Platform Intake Chatbot.
Be clear, concise, and honest about capabilities.
"""

# ------------------------------------------------------------------
# Session State
# ------------------------------------------------------------------

chat_history = [SystemMessage(content=SYSTEM_PROMPT)]

glue_intake_active = False
awaiting_final_confirmation = False
session_closed = False

glue_data = {}
current_field = None

# ------------------------------------------------------------------
# Glue DB Fields
# ------------------------------------------------------------------

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
    "intake_id": "Do you have an intake ID for this request?",
    "database_name": "What should we name the Glue database?",
    "database_s3_location": "What is the S3 location for this database?",
    "database_description": "Can you give a short description of the database?",
    "aws_account_id": "Which AWS account ID will host this?",
    "region": "Which AWS region should this be created in?",
    "data_construct": "What data construct does this belong to?",
    "data_env": "Which environment is this for (dev, qa, prod)?",
    "data_layer": "Which data layer does this belong to?",
    "source_name": "What is the source system name?",
    "enterprise_or_func_name": "Is this enterprise or function owned? What’s the name?",
    "enterprise_or_func_subgrp_name": "What is the sub-group name?",
    "data_owner_email": "What is the data owner’s email?",
    "data_owner_github_uname": "What is the data owner’s GitHub username?",
    "data_leader": "Who is the data leader?",
}

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def get_next_field():
    for field in REQUIRED_FIELDS:
        if field not in glue_data:
            return field
    return None


def is_negative_confirmation(text: str) -> bool:
    text = text.lower()
    return any(
        x in text
        for x in ["no", "nope", "nothing", "all good", "done", "that's all"]
    )

# ------------------------------------------------------------------
# Main Entry
# ------------------------------------------------------------------

def ask_groq(user_input: str) -> str:
    global glue_intake_active
    global awaiting_final_confirmation
    global session_closed
    global current_field

    if session_closed:
        return "✅ Session complete. Start a new request anytime."

    user_lower = user_input.lower()

    # ---------------- CAPABILITIES ----------------
    if "what pr" in user_lower or "support" in user_lower:
        return (
            "I support the following PRs:\n\n"
            "• Glue Database PRs ✅\n"
            "• IAM PRs 🚧 (in progress)\n"
            "• Resource Policy PRs 🚧 (in progress)"
        )

    # ---------------- UNSUPPORTED ----------------
    if "iam" in user_lower or "resource policy" in user_lower:
        return "This service is currently under development. Please check back later."

    # ---------------- START GLUE FLOW ----------------
    if not glue_intake_active and "glue" in user_lower:
        glue_intake_active = True
        current_field = get_next_field()
        return (
            "Great 👍 Let’s get your Glue Database PR started.\n\n"
            + FIELD_QUESTIONS[current_field]
        )

    # ---------------- COLLECT GLUE DATA ----------------
    if glue_intake_active and not awaiting_final_confirmation:
        # Save the answer to the current field
        glue_data[current_field] = user_input.strip()

        # Move to next field
        current_field = get_next_field()

        if current_field:
            return FIELD_QUESTIONS[current_field]
        else:
            awaiting_final_confirmation = True
            return (
                "Thanks! I’ve captured all required details.\n\n"
                "Is there anything else you’d like to add?"
            )

    # ---------------- FINAL CONFIRMATION ----------------
    if awaiting_final_confirmation:
        if is_negative_confirmation(user_lower):
            session_closed = True
            return (
                "✅ All required details are collected. Ready to generate config.\n"
                "You can close the session now."
            )
        else:
            return "Got it 👍 You can add more details or say 'no' when done."

    # ---------------- GENERAL Q&A ----------------
    try:
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_input)
        ])
        return response.content
    except Exception as e:
        print("LLM ERROR:", repr(e))
        return "⚠️ Language service error. Try again or start a Glue DB PR."
