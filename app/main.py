"""
Main entry point.

NOTE:
Chatbot interaction is now handled via FastAPI (api.py)
and consumed by a browser extension UI.
"""

def main():
    print(
        "\nThis project now runs as a backend service.\n"
        "Please start the API using:\n\n"
        "uvicorn app.api:app --reload\n"
    )


if __name__ == "__main__":
    main()
