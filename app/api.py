from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from app.tools.glue_pr_tool import create_glue_db_pr, GlueDBPRInput

load_dotenv()

# -------------------------------
# LLM (GENERAL CHAT ONLY)
# -------------------------------
plain_llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant",
    temperature=0.1,
)

app = FastAPI(title="Data Platform Intake Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Intake State (POC)
# -------------------------------
SESSION_DATA: Dict[str, str] = {}
INTAKE_ACTIVE = False

REQUIRED_FIELDS = [
    "intake_id",
    "database_name",
    "database_s3_location",
    "database_description",
    "aws_account_id",
    "source_name",
    "enterprise_or_func_name",
    "enterprise_or_func_subgrp_name",
    "region",
    "data_construct",
    "data_env",
    "data_layer",
    "data_leader",
    "data_owner_email",
    "data_owner_github_uname",
    "pr_title",
]


def get_next_field():
    for field in REQUIRED_FIELDS:
        if field not in SESSION_DATA:
            return field
    return None


def is_start_intake(text: str) -> bool:
    t = text.lower().strip()
    return any(
        phrase in t
        for phrase in [
            "create glue",
            "create gluedb",
            "gluedb creation",
            "start gluedb",
            "yes",
            "ok lets start",
            "let's start",
        ]
    )


class ChatRequest(BaseModel):
    messages: List[dict]


@app.post("/chat")
def chat(req: ChatRequest):
    global INTAKE_ACTIVE

    user_msg = req.messages[-1]["content"].strip()

    # =================================================
    # MODE 1 — BEFORE INTAKE (GENERAL CHAT)
    # =================================================
    if not INTAKE_ACTIVE:
        # Explicit start of intake
        if is_start_intake(user_msg):
            INTAKE_ACTIVE = True
            SESSION_DATA.clear()
            return {
                "response": "Great 👍 Let’s start.\nWhat is the intake ID?"
            }

        # General product-scoped chat ONLY
        response = plain_llm.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "You are the Data Platform Intake Bot.\n"
                        "You ONLY support creating automated Glue Database Pull Requests.\n"
                        "If asked about supported PRs, say you support Glue Database PR creation.\n"
                        "Do NOT invent intake steps.\n"
                        "If the user wants to start, instruct them to say 'create glue db'."
                    ),
                }
            ] + req.messages
        )
        return {"response": response.content}

    # =================================================
    # MODE 2 — INTAKE IN PROGRESS (BACKEND ONLY)
    # =================================================
    next_field = get_next_field()
    SESSION_DATA[next_field] = user_msg

    next_field = get_next_field()

    # All fields collected → CREATE PR
    if not next_field:
        result = create_glue_db_pr(
            GlueDBPRInput(**SESSION_DATA)
        )
        SESSION_DATA.clear()
        INTAKE_ACTIVE = False
        return {"response": result}

    # Ask next REQUIRED field (mandatory)
    return {
        "response": f"What is the {next_field.replace('_', ' ')}?"
    }
