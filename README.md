# Data Platform Intake Bot 🤖

AI-powered chatbot for automated Glue Database Pull Request creation. Built with LangChain, Groq LLM, and FastAPI.

## 🌟 Features

- **LLM-Driven Conversations**: Natural language interface powered by Llama 3.1
- **Intelligent Field Collection**: Automatically gathers required information through conversation
- **Automated PR Creation**: Creates GitHub Pull Requests with YAML configurations
- **Chrome Extension**: Seamlessly integrates into GitHub UI
- **Input Validation**: Ensures data quality before PR creation

## 📋 Prerequisites

- Python 3.8+
- Git installed and configured
- GitHub account with repository access
- Groq API account

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/data-platform-intake-bot.git
cd data-platform-intake-bot
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your actual values
# Required variables:
# - GROQ_API_KEY: Get from https://console.groq.com/keys
# - GITHUB_TOKEN: Get from https://github.com/settings/tokens
# - REPO_NAME: Target repository (format: owner/repo)
# - BASE_BRANCH: Usually 'main' or 'dev'
```

### 4. Run the Backend Server

```bash
# Start the FastAPI server
uvicorn app.api:app --reload

# Server will start at: http://127.0.0.1:8000
# API docs available at: http://127.0.0.1:8000/docs
```

### 5. Install Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `github-extension` folder
5. Navigate to any GitHub page to see the chatbot

## 📁 Project Structure

```
data-platform-intake-bot/
├── app/
│   ├── __init__.py
│   ├── api.py                      # Main FastAPI application
│   ├── llm/
│   │   ├── __init__.py
│   │   └── groq_client.py          # LLM configuration (optional)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── git_ops.py              # Git operations
│   │   └── yaml_generator.py       # YAML file generation
│   └── tools/
│       ├── __init__.py
│       └── glue_pr_tool.py         # LangChain tool definition
├── github-extension/
│   ├── content.js                  # Chrome extension script
│   ├── style.css                   # Chatbot UI styles
│   └── manifest.json               # Extension configuration
├── intake_configs/                 # Generated YAML files
├── .env.example                    # Environment template
├── .gitignore
├── requirements.txt
└── README.md
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key for LLM | `gsk_...` |
| `GITHUB_TOKEN` | GitHub Personal Access Token | `ghp_...` |
| `REPO_NAME` | Target repository for PRs | `company/data-configs` |
| `BASE_BRANCH` | Base branch for PRs | `dev` or `main` |

### GitHub Token Permissions

Your GitHub token needs the following scopes:
- ✅ `repo` (full control of private repositories)

## 💬 Usage

### Starting a Conversation

1. Navigate to any GitHub page
2. The chatbot appears in the bottom-right corner
3. Say: "I want to create a Glue Database PR"
4. Follow the bot's questions

### Required Information

The bot will collect 16 fields:

1. **intake_id** - Unique identifier (e.g., INT-12345)
2. **database_name** - Glue database name
3. **database_s3_location** - S3 path (s3://bucket/path)
4. **database_description** - Purpose description
5. **aws_account_id** - 12-digit AWS account ID
6. **source_name** - Source system name
7. **enterprise_or_func_name** - Enterprise area
8. **enterprise_or_func_subgrp_name** - Sub-group
9. **region** - AWS region (e.g., us-east-1)
10. **data_construct** - Data construct type
11. **data_env** - Environment (dev/staging/prod)
12. **data_layer** - Data layer (raw/curated/analytics)
13. **data_leader** - Data owner name
14. **data_owner_email** - Owner email
15. **data_owner_github_uname** - GitHub username
16. **pr_title** - Pull Request title

### Example Conversation

```
You: I want to create a Glue Database PR

Bot: Great! Let's start. What is the intake ID?

You: INT-12345

Bot: Got it. What would you like to name the database?

You: analytics_prod_db

Bot: Perfect. What is the S3 location for the database?

You: s3://my-company-data/analytics/prod

... (continues until all fields collected)

Bot: ✅ Pull Request created successfully!
     🔗 https://github.com/company/repo/pull/123
```

## 🧪 Testing

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

### List Available Tools

```bash
curl http://127.0.0.1:8000/tools
```

### Test Chat API

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

## 🛠️ Development

### Running in Development Mode

```bash
# Auto-reload on code changes
uvicorn app.api:app --reload --log-level debug
```

### Adding New PR Types

1. Create a new tool in `app/tools/`
2. Define Pydantic input schema
3. Implement PR creation function
4. Add tool to `app/api.py`
5. Update system prompt with new capabilities

## 🐛 Troubleshooting

### Backend Not Reachable

- Ensure server is running: `uvicorn app.api:app --reload`
- Check port 8000 is not in use
- Verify CORS settings if accessing from different domain

### GitHub API Errors

- **401 Unauthorized**: Check `GITHUB_TOKEN` in `.env`
- **404 Not Found**: Verify `REPO_NAME` and repository access
- **422 Unprocessable**: PR branch might already exist

### Git Operation Failures

- Ensure repository is clean (no uncommitted changes)
- Verify Git is configured with user name and email
- Check network connection for `git pull/push`

## 📝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 🔒 Security

- **Never commit `.env` file**
- Rotate tokens if accidentally exposed
- Use environment-specific tokens (dev/prod)
- Review PR permissions before granting

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com/)
- Powered by [Groq](https://groq.com/)
- FastAPI framework by [Tiangolo](https://fastapi.tiangolo.com/)

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Contact the Data Platform team
- Check internal documentation

---

Made with ❤️ by the Data Platform Team
