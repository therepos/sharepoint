# Repo conventions for Claude

## Pull requests
- After pushing a feature branch, always open a PR targeting `main` (via the GitHub MCP `create_pull_request` tool) without waiting for the user to ask. Include a Summary and a Test plan section in the body.
- Subscribe the session to PR activity (`subscribe_pr_activity`) so CI failures and review comments wake this conversation.
