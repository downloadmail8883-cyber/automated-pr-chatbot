"""
Handles conversational intake flow for the Automated PR Chatbot.
"""

from chatbot import ask_groq


def collect_intake():
    """
    Entry point for conversational chatbot intake.
    Determines user intent and routes accordingly.
    """

    print("🤖 Hi! I’m the Data Platform Intake Bot.")
    print(
        "I can help you with:\n"
        "• Creating Glue Database PRs\n"
        "• Answering questions about DevOps, data platforms, and processes\n"
        "• IAM and Resource Policy PRs (coming soon)\n"
    )

    user_input = input("👉 How can I help you today?\n👤 ").strip()

    intent = user_input.lower()

    # INTENT: GLUE DATABASE PR
    if "glue" in intent and "pr" in intent:
        print("\n👍 Got it — you want to create a Glue Database PR.")
        return collect_glue_db_intake()

    # INTENT: UNSUPPORTED PR FLOWS
    if "iam" in intent or "resource policy" in intent or "policy" in intent:
        print(
            "\n⚠️ This PR workflow is currently under development.\n"
            "Please reach out to the platform team or try again later.\n"
        )
        return {}

    # INTENT: GENERAL QUESTIONS
    print("\n🤖 Let me help with that.\n")
    response = ask_groq(user_input)
    print(response)

    print(
        "\nℹ️ If you’d like to create a Glue Database PR, "
        "just tell me and I’ll guide you through it.\n"
    )

    return {}


def collect_glue_db_intake():
    """
    Conversational Glue Database PR intake.
    """

    collected_data = {}

    print(
        "\n🛠️ I’ll guide you through creating a Glue Database PR.\n"
        "You can answer naturally — I’ll ask only what’s needed.\n"
    )

    collected_data["intake_id"] = ask("What is the intake ID? (example: M0000562)")
    collected_data["data_env"] = ask("Which environment is this for? (dev / qa / prd)")
    collected_data["data_layer"] = ask(
        "Which data layer does this belong to? (raw / curated / semantic)"
    )
    collected_data["source_name"] = ask("What is the source system name?")
    collected_data["enterprise_or_func_name"] = ask(
        "What is the enterprise or functional group?"
    )
    collected_data["enterprise_or_func_subgrp_name"] = ask(
        "What is the sub-group under that?"
    )
    collected_data["database_name"] = ask("What database name would you like to use?")
    collected_data["database_s3_location"] = ask(
        "Where should this database be stored in S3?"
    )
    collected_data["database_description"] = ask(
        "Can you briefly describe what this database is used for?"
    )
    collected_data["aws_account_id"] = ask("Which AWS account ID should be used?")
    collected_data["region"] = ask("Which AWS region should this be created in?")
    collected_data["data_construct"] = ask(
        "What is the data construct? (Source / Consumer)"
    )
    collected_data["data_owner_email"] = ask(
        "Who is the data owner? Please provide their email."
    )
    collected_data["data_owner_github_uname"] = ask(
        "What is the GitHub username of the data owner?"
    )
    collected_data["data_leader"] = ask(
        "Who is the data leader responsible for this dataset?"
    )

    # SUMMARY
    print("\n📋 Here’s a summary of what I collected:\n")
    for key, value in collected_data.items():
        print(f"• {key}: {value}")

    print("\n✅ All required details are collected. Ready to generate config.\n")

    return collected_data


def ask(prompt: str) -> str:
    """
    Ask a conversational question and ensure a non-empty response.
    """
    while True:
        value = input(f"🤖 {prompt}\n👤 ").strip()
        if value:
            return value
        print("⚠️ This information is required. Please provide a value.\n")
