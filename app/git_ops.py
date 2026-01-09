"""
Handles Git operations: branch creation, commit, push, and PR creation.
"""
import os
from git import Repo
import requests

def create_branch_and_commit(repo_path: str, branch_name: str, file_path: str, content: str):
    """Create a branch, add file, commit, and push."""
    repo = Repo(repo_path)
    git = repo.git

    # Create branch from current HEAD
    if branch_name in repo.branches:
        git.checkout(branch_name)
    else:
        git.checkout('HEAD', b=branch_name)

    # Write content to file
    with open(file_path, 'w') as f:
        f.write(content)

    # Stage and commit
    repo.index.add([file_path])
    repo.index.commit(f"Add intake config: {os.path.basename(file_path)}")

    # Push branch
    origin = repo.remote(name='origin')
    origin.push(branch_name)
    print(f"Branch '{branch_name}' pushed to remote.")

def create_pull_request(github_token: str, repo_name: str, branch_name: str, base: str):
    """Create a GitHub PR using GitHub API."""
    url = f"https://api.github.com/repos/{repo_name}/pulls"
    headers = {"Authorization": f"token {github_token}"}
    data = {
        "title": f"Intake Config: {branch_name}",
        "head": branch_name,
        "base": base,
        "body": f"Automated intake PR for branch {branch_name}"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Failed to create PR: {response.status_code} {response.text}")
