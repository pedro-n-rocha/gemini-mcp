# Gemini CLI MCP Server

An MCP (Model Context Protocol) server that provides Google Search grounding capabilities using Gemini Code Assist. This server enables LLMs like Claude to perform web searches with citations and source attribution.

## Features

- **Google Search Grounding**: Get answers with real-time web search results
- **Source Citations**: Responses include source URLs and citation mapping
- **Automatic Token Refresh**: OAuth credentials are automatically refreshed when expired
- **Docker Support**: Run as a containerized service with stdio or HTTP/SSE transport
- **Multiple Models**: Support for various Gemini models

## Prerequisites

- Python 3.11+
- A Google account with access to Gemini Code Assist
- A Google OAuth client (set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`) it is out there somewhere , search for it 


## Installation

### Local Installation

1. Clone or download this directory
2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

### Docker Installation

Build the Docker image:

```bash
docker build -t gemini-mcp .
```

## Authentication Setup

Before using any scripts, you need to authenticate with Google.

### Local Authentication

```bash
# Option A: export env vars
export GOOGLE_OAUTH_CLIENT_ID="...apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="..."
python manual_auth.py
```

### Docker Authentication

```bash
docker run -it --rm -e GOOGLE_OAUTH_CLIENT_ID="..." -e GOOGLE_OAUTH_CLIENT_SECRET="..." -p 8080:8080 -v ./config:/app/config gemini-mcp
```

On first run (when no credentials exist), the container will:
1. Display a URL to open in your browser for Google OAuth login
2. Guide you to paste the redirect URL back
3. Save your credentials to the config directory
4. Print your credential/project info
5. Start the MCP server in HTTP/SSE mode on port 8080

**Important**: Keep your credentials secure and never commit them to version control.

## Docker Usage (HTTP/SSE)

The Docker container always starts the MCP server in HTTP/SSE mode.

### Examples

```bash
# First run (interactive OAuth + start server)
docker run -it --rm -p 8080:8080 -v ./config:/app/config gemini-mcp

# Subsequent runs (no -it needed once credentials exist)
docker run -d -p 8080:8080 -v ./config:/app/config gemini-mcp
```

## Available Scripts

### `server.py` - MCP Server

The main MCP server that exposes the `google_search` tool.

```bash
# Run directly (defaults to HTTP/SSE on :8080)
python server.py

# If you need stdio transport (some MCP clients), set:
MCP_TRANSPORT=stdio python server.py
```

The server provides the following tool:

- **`google_search(query, model)`**: Search using Gemini with Google Search grounding
  - `query`: The search query or question
  - `model`: The model to use (default: `gemini-2.5-flash`)

### `search.py` - CLI Search

A command-line interface for quick searches without running the full MCP server.

```bash
# Basic search
python search.py "What is the latest news about AI?"

# Specify a model
python search.py "Explain quantum computing" --model gemini-2.5-pro

# Get help
python search.py --help
```

### `info.py` - Credential Info

Display information about your current credentials and authentication status.

```bash
python info.py
```

This shows:
- User email and name
- Current tier and managed project
- Available tiers

### `manual_auth.py` - Authentication

Perform OAuth authentication and save credentials.

```bash
python manual_auth.py
```

## Available Models

The following Gemini models are supported:

| Model | Description |
|-------|-------------|
| `gemini-2.5-flash` | Fast, efficient model (default) |
| `gemini-2.5-pro` | More capable model for complex tasks |
| `gemini-2.0-flash` | Previous generation flash model |
| `gemini-1.5-flash` | Legacy flash model |
| `gemini-1.5-pro` | Legacy pro model |

## MCP Client Configuration

For clients that support HTTP/SSE transport, run the server in HTTP mode:

```bash
docker run -d -p 8080:8080 -v ./config:/app/config gemini-mcp
```

Then configure your MCP client:

```json
{
  "mcpServers": {
    "gemini-search": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CREDENTIALS_PATH` | Path to credentials.json | `./credentials.json` (local) or `/app/config/credentials.json` (Docker) |
| `HOST` | HTTP bind address | `0.0.0.0` |
| `PORT` | HTTP port | `8080` |
| `MCP_TRANSPORT` | MCP transport (`sse` or `stdio`) | `sse` |

### Setting Environment Variables

**Local**:
```bash
export CREDENTIALS_PATH=/path/to/credentials.json
python server.py
```
### Manual Google Cloud Setup

If automatic provisioning fails, you may need to set up the project manually:

1. Go to the Google Cloud Console.
2. Create or select a project.
3. Enable the Gemini for Google Cloud API (`cloudaicompanion.googleapis.com`).
4. Configure the `projectId` in your Opencode config as shown above.

### Gemini Admin Settings

In Google Cloud Console, search for **Admin for Gemini**. Open it, go to **Settings**, then enable **Preview** on release channels for **Gemini Code Assist in local IDEs**.
