import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import StructuredTool

from app.tools.glue_pr_tool import create_glue_db_pr, GlueDBPRInput

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant",
    temperature=0.1,
)

glue_pr_tool = StructuredTool.from_function(
    func=create_glue_db_pr,
    name="create_glue_database_pr",
    description="Create a GitHub Pull Request for a Glue Database intake.",
    args_schema=GlueDBPRInput,
)

tools = [glue_pr_tool]


def chat_with_tools(messages):
    return llm.bind_tools(tools).invoke(messages)
