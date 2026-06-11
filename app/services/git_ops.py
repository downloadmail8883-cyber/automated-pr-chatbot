"""
Git Operations Service
Enhanced with better PR conflict detection and handling
"""

import os
from typing import Dict, Any
from git import Repo
import requests


def get_authenticated_username(github_token: str) -> str:
    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 200:
        login = response.json().get("login")
        if login:
            return login

    raise RuntimeError(
        "Unable to determine the authenticated GitHub user from GITHUB_TOKEN1. "
        "Please verify that the token is valid and has access to the fork."
    )


def create_pull_request(
    github_token: str,
    repo_name: str,
    pr_title: str,
    pr_body: str = None,
    head_branch: str = "dev",
    base_branch: str = None,
    head_owner: str = None,
) -> Dict[str, Any]:
    """
    Create PR from fork dev -> upstream dev
    Enhanced with better error messages for PR conflicts
    """

    base_branch = base_branch or os.getenv("BASE_BRANCH", "dev")
    fork_owner = head_owner or get_authenticated_username(github_token)

    url = f"https://api.github.com/repos/{repo_name}/pulls"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if pr_body is None:
        pr_body = (
            "## Automated Data Platform Intake\n\n"
            "This PR was generated automatically by the Data Platform Intake Bot.\n\n"
            "- Source: fork `dev` branch\n"
            "- Target: upstream `dev` branch\n"
        )

    # The head should be in format: "username:branch"
    payload = {
        "title": pr_title,
        "head": f"{fork_owner}:{head_branch}" if head_owner else head_branch,
        "base": base_branch,
        "body": pr_body,
        "maintainer_can_modify": False,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 201:
            return response.json()

        # Handle specific error cases
        error_data = response.json()

        if response.status_code == 422:
            # Check if it's a duplicate PR error
            if "pull request already exists" in str(error_data).lower():
                # Try to get the existing PR URL
                existing_pr_url = get_existing_pr_url(
                    github_token,
                    repo_name,
                    fork_owner,
                    head_branch,
                    base_branch,
                    use_owner=bool(head_owner),
                )

                raise RuntimeError(
                    f"A pull request already exists from {payload['head']} to {repo_name}:{base_branch}.\n"
                    f"Existing PR: {existing_pr_url if existing_pr_url else 'Check your PRs on GitHub'}\n\n"
                    "Options:\n"
                    "1. Close the existing PR and create a new one\n"
                    "2. Your changes have been pushed to the source branch and will appear in the existing PR"
                )
            else:
                raise RuntimeError(f"GitHub API validation error: {error_data}")

        elif response.status_code == 401:
            raise RuntimeError(
                "Authentication failed. Please check your GITHUB_TOKEN in .env file."
            )

        elif response.status_code == 404:
            raise RuntimeError(
                f"Repository '{repo_name}' not found or you don't have access. "
                "Please verify REPO_NAME in .env file."
            )

        else:
            raise RuntimeError(
                f"GitHub API error (status {response.status_code}): {response.text}"
            )

    except requests.exceptions.Timeout:
        raise RuntimeError("GitHub API request timed out. Please try again.")

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Failed to connect to GitHub API. "
            "Please check your internet connection."
        )

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"GitHub API request failed: {str(e)}")


def get_existing_pr_url(
    github_token: str,
    repo_name: str,
    fork_owner: str,
    head_branch: str,
    base_branch: str,
    use_owner: bool = True,
) -> str:
    """
    Get URL of existing PR from fork to upstream
    """
    try:
        url = f"https://api.github.com/repos/{repo_name}/pulls"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }

        params = {
            "state": "open",
            "head": f"{fork_owner}:{head_branch}" if use_owner else head_branch,
            "base": base_branch
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            prs = response.json()
            if prs and len(prs) > 0:
                return prs[0]["html_url"]

        return None

    except Exception:
        return None


def check_existing_pr(github_token: str, repo_name: str, fork_owner: str) -> Dict[str, Any]:
    """
    Check if there's an existing open PR from fork dev to upstream dev

    Returns:
        Dictionary with 'exists' (bool) and 'url' (str if exists)
    """
    try:
        url = f"https://api.github.com/repos/{repo_name}/pulls"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }

        params = {
            "state": "open",
            "head": f"{fork_owner}:dev",
            "base": "dev"
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            prs = response.json()
            if prs and len(prs) > 0:
                return {
                    "exists": True,
                    "url": prs[0]["html_url"],
                    "title": prs[0]["title"],
                    "number": prs[0]["number"]
                }

        return {"exists": False}

    except Exception as e:
        print(f"Error checking existing PR: {e}")
        return {"exists": False}