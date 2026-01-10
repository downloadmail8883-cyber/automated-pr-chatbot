# """
# Main entry point for the Automated PR Chatbot.

# Flow:
# 1. Collect mandatory intake data via CLI
# 2. Generate YAML configuration
# 3. Save YAML using database_name.yaml
# 4. Create Git branch, commit YAML
# 5. Push branch and raise PR automatically
# """

# import os
# from intake_flow import collect_intake
# from yaml_generator import generate_yaml
# from git_ops import create_branch_and_commit, create_pull_request


# def main():
#     print("\nHello! I'm the Data Platform Intake Bot, ready to help you configure your new data intake.\n")


# # Step 1: Collect intake details

#     collected_data = collect_intake()


# # # Step 2: Generate YAML

# #     yaml_content = generate_yaml(collected_data)

# #     print("\nGenerated YAML:\n")
# #     print(yaml_content)


# # # Step 3: Resolve repo root safely (works on Windows/Linux/Mac)

# #     REPO_ROOT = os.path.abspath(
# #         os.path.join(os.path.dirname(__file__), "..")
# #     )

# #  # Step 4: Save YAML using database_name.yaml

# #     yaml_dir = os.path.join(REPO_ROOT, "intake_configs")
# #     os.makedirs(yaml_dir, exist_ok=True)

# #     yaml_filename = f"{collected_data['database_name']}.yaml"
# #     yaml_file_path = os.path.join(yaml_dir, yaml_filename)

# #     with open(yaml_file_path, "w") as f:
# #         f.write(yaml_content)

# #     print(f"\nYAML file saved at:\n{yaml_file_path}")


# # # Step 5: Create branch + commit YAML

# #     branch_name = "dev"

# #     create_branch_and_commit(
# #         repo_path=REPO_ROOT,
# #         branch_name=branch_name,
# #         file_path=yaml_file_path,
# #         content=yaml_content
# #     )

# # # Step 6: Create Pull Request
# #     github_token = os.getenv("GITHUB_TOKEN")
# #     repo_name = os.getenv("REPO_NAME")
# #     base_branch = os.getenv("BASE_BRANCH", "dev")

# #     pr_response = create_pull_request(
# #         github_token=github_token,
# #         repo_name=repo_name,
# #         branch_name=branch_name,
# #         base=base_branch
# #     )

# #     print("\nPull Request created successfully 🎉")
# #     print(f"PR URL: {pr_response['html_url']}")


# if __name__ == "__main__":
#     main()

from chatbot import ask_groq

EXIT_COMMANDS = {"exit", "quit", "close", "close it", "done"}

def main():
    print("\n🤖 Hi! I’m the Data Platform Intake Bot.")
    print("👉 Type 'exit', 'quit', or 'close' to end the session.\n")

    while True:
        user_input = input("👤 ").strip()

        # User explicitly wants to exit
        if user_input.lower() in EXIT_COMMANDS:
            print("\n🤖 Session closed. Goodbye 👋")
            break

        response = ask_groq(user_input)
        print(f"\n🤖 {response}\n")

        # Chatbot indicates session completion
        if response.startswith("✅ Session complete"):
            print("🤖 Session closed. Goodbye 👋")
            break


if __name__ == "__main__":
    main()
