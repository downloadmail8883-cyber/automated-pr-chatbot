import os
import traceback
from pydantic import BaseModel

from app.services.yaml_generator import generate_yaml
from app.services.git_ops import create_branch_and_commit, create_pull_request


class GlueDBPRInput(BaseModel):
    intake_id: str
    database_name: str
    database_s3_location: str
    database_description: str
    aws_account_id: str
    source_name: str
    enterprise_or_func_name: str
    enterprise_or_func_subgrp_name: str
    region: str
    data_construct: str
    data_env: str
    data_layer: str
    data_leader: str
    data_owner_email: str
    data_owner_github_uname: str
    pr_title: str


def create_glue_db_pr(input: GlueDBPRInput) -> str:
    try:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        yaml_dir = os.path.join(repo_root, "intake_configs")
        os.makedirs(yaml_dir, exist_ok=True)

        yaml_path = os.path.join(
            yaml_dir, f"{input.database_name}.yaml"
        )

        branch_name = f"intake/{input.intake_id}"

        yaml_content = generate_yaml(
            input.dict(exclude={"pr_title"})
        )

        create_branch_and_commit(
            repo_path=repo_root,
            branch_name=branch_name,
            yaml_file_path=yaml_path,
            yaml_content=yaml_content,
        )

        pr = create_pull_request(
            github_token=os.getenv("GITHUB_TOKEN"),
            repo_name=os.getenv("REPO_NAME"),
            branch_name=branch_name,
            base_branch=os.getenv("BASE_BRANCH", "main"),
            pr_title=input.pr_title,
        )

        return (
            "✅ Pull Request created successfully\n"
            f"🔗 {pr['html_url']}"
        )

    except Exception as e:
        traceback.print_exc()
        return (
            "❌ PR creation failed.\n\n"
            f"Reason:\n{str(e)}"
        )
