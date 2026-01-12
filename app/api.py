from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.chatbot import ask_groq
from app.yaml_generator import generate_yaml
from app.git_ops import create_branch_and_commit, create_pull_request
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(req: ChatRequest):
    result = ask_groq(req.message)

    # NORMAL MESSAGE
    if result["type"] == "message":
        return {"response": result["content"]}

    # ACTION: CREATE PR
    if result["type"] == "action" and result["action"] == "create_pr":
        data = result["data"]

        yaml_content = generate_yaml(data)

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        yaml_dir = os.path.join(repo_root, "intake_configs")
        os.makedirs(yaml_dir, exist_ok=True)

        file_path = os.path.join(yaml_dir, f"{data['database_name']}.yaml")
        with open(file_path, "w") as f:
            f.write(yaml_content)

        branch_name = f"intake/{data['intake_id']}"

        create_branch_and_commit(
            repo_path=repo_root,
            branch_name=branch_name,
            file_path=file_path,
            content=yaml_content
        )

        pr = create_pull_request(
            github_token=os.getenv("GITHUB_TOKEN"),
            repo_name=os.getenv("REPO_NAME"),
            branch_name=branch_name,
            base=os.getenv("BASE_BRANCH", "dev")
        )

        return {
            "response": (
                "🚀 PR successfully created!\n\n"
                f"🔗 {pr['html_url']}"
            )
        }
