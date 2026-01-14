import os
from git import Repo
import requests


def create_branch_and_commit(repo_path, branch_name, yaml_file_path, yaml_content):
    repo = Repo(repo_path)
    git = repo.git

    if repo.is_dirty(untracked_files=True):
        raise RuntimeError("Repo has uncommitted changes.")

    git.checkout("main")
    git.pull("origin", "main")
    git.checkout("-b", branch_name)

    os.makedirs(os.path.dirname(yaml_file_path), exist_ok=True)
    with open(yaml_file_path, "w") as f:
        f.write(yaml_content)

    repo.index.add([yaml_file_path])
    repo.index.commit(f"Add Glue DB config: {os.path.basename(yaml_file_path)}")
    repo.remote("origin").push(branch_name)


def create_pull_request(github_token, repo_name, branch_name, base_branch, pr_title):
    url = f"https://api.github.com/repos/{repo_name}/pulls"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }

    payload = {
        "title": pr_title,
        "head": branch_name,
        "base": base_branch,
        "body": "Automated Glue Database intake configuration.",
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 201:
        raise RuntimeError(response.text)

    return response.json()
