import os
from typing import Optional

from dotenv import load_dotenv

try:
    from langchain_groq import ChatGroq
except ImportError:  # pragma: no cover
    ChatGroq = None


load_dotenv()


def is_groq_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def get_llm() -> Optional[object]:
    if not is_groq_configured() or ChatGroq is None:
        return None

    try:
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            temperature=0,
        )
    except Exception:
        return None