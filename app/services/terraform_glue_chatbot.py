import os
from typing import Dict, Optional


TERRAFORM_CONTEXT = (
    "Glue Terraform intake is running in fallback mode. "
    "Send a message describing the Glue job you want to generate, and the service will echo the request context "
    "until the full LangGraph implementation is restored."
)

_sessions: Dict[str, Dict[str, str]] = {}


def terraform_ai_enabled() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def reset_terraform_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def run_terraform_chat_turn(session_id: str, message: Optional[str]) -> Dict[str, object]:
    session = _sessions.setdefault(session_id, {"last_message": ""})
    cleaned_message = (message or "").strip()

    if not cleaned_message:
        response = (
            "Terraform intake is available, but the advanced guided flow is not installed in this workspace snapshot. "
            "Describe the Glue job you want to generate to continue."
        )
    else:
        session["last_message"] = cleaned_message
        response = (
            "Received your Terraform intake request. "
            "The fallback chatbot is active, so no Terraform file was generated yet. "
            f"Last request: {cleaned_message}"
        )

    return {
        "response": response,
        "completed": False,
        "terraform_output": None,
        "output_path": None,
        "answers": dict(session),
        "context": TERRAFORM_CONTEXT,
        "ai_enabled": terraform_ai_enabled(),
    }