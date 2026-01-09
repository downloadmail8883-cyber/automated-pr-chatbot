"""
Handles interaction with Gemini LLM.
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise Exception("GOOGLE_API_KEY is not set in .env")

# Initialize Gemini model
llm = ChatGoogleGenerativeAI(model='gemini-1.5-flash', temperature=0, api_key=GOOGLE_API_KEY)

SYSTEM_PROMPT = """
You are a friendly and professional Data Platform Intake Bot. Ask questions clearly and politely.
You are Data Platform Intake Bot.

Your job is to:
1. Collect required metadata for creating a data intake configuration.
2. Ask one question at a time.
3. Maintain a friendly, professional DevOps assistant tone.
4. Never generate YAML or code unless explicitly asked.
5. If a value is already provided, do not ask again.
6. Once all fields are collected, respond with:
   'All required details are collected. Ready to generate config.'

Required fields:
- intake_id
- database_name
- database_s3_location
- database_description
- aws_account_id
- region
- data_construct
- data_env
- data_layer
- source_name
- enterprise_or_func_name
- enterprise_or_func_subgrp_name
- data_owner_email
- data_owner_github_uname
- data_leader
"""

chat_history = [SystemMessage(content=SYSTEM_PROMPT)]

def ask_gemini(user_input: str) -> str:
    """Send a user message to Gemini and return its response, maintaining chat history."""
    chat_history.append(HumanMessage(content=user_input))
    response = llm.invoke(chat_history)
    chat_history.append(response)
    return response.content
