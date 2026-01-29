#!/usr/bin/env python3
"""MCP Server for Gemini Code Assist."""

import json
import os
from datetime import datetime, timedelta, timezone

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from fastmcp import FastMCP

# Constants
ENDPOINT = "https://cloudcode-pa.googleapis.com/v1internal"

# Initialize MCP server
mcp = FastMCP("gemini-code-assist")


def get_credentials_path() -> str:
    """Get the path to credentials.json.
    
    Checks for CREDENTIALS_PATH env var first (for Docker),
    then falls back to local file.
    """
    return os.environ.get("CREDENTIALS_PATH", os.path.join(os.path.dirname(__file__), "credentials.json"))


def get_session() -> str:
    """Load credentials, refresh if needed, and return the access token."""
    creds_path = get_credentials_path()

    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            "credentials.json not found. Please run manual_auth.py first to authenticate."
        )

    with open(creds_path, "r") as f:
        creds_data = json.load(f)

    expiry = None
    expiry_raw = creds_data.get("expiry")
    if isinstance(expiry_raw, str) and expiry_raw:
        try:
            expiry = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00"))
        except ValueError:
            expiry = None
    else:
        obtained_at_raw = creds_data.get("obtained_at")
        expires_in_raw = creds_data.get("expires_in")
        if isinstance(obtained_at_raw, str) and obtained_at_raw and expires_in_raw is not None:
            try:
                obtained_at = datetime.fromisoformat(obtained_at_raw.replace("Z", "+00:00"))
                if obtained_at.tzinfo is None:
                    obtained_at = obtained_at.replace(tzinfo=timezone.utc)
                expires_in = float(expires_in_raw)
                expiry = obtained_at + timedelta(seconds=expires_in)
            except (ValueError, TypeError):
                expiry = None

    scopes = None
    scope_raw = creds_data.get("scope")
    if isinstance(scope_raw, str) and scope_raw.strip():
        scopes = scope_raw.split()

    creds = Credentials(
        token=creds_data.get("access_token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data.get("client_id"),
        client_secret=creds_data.get("client_secret"),
        scopes=scopes,
        expiry=expiry,
    )

    # Refresh if expired (or if expiry is missing, refresh once to learn it)
    if (creds.expired or creds.expiry is None) and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed credentials
        creds_data["access_token"] = creds.token
        if creds.expiry is not None:
            now = datetime.now(timezone.utc)
            creds_data["obtained_at"] = now.isoformat()
            creds_data["expiry"] = creds.expiry.astimezone(timezone.utc).isoformat()
        with open(creds_path, "w") as f:
            json.dump(creds_data, f, indent=2)

    return creds.token


def get_default_tier_id(allowed_tiers: list) -> str:
    """Get the default tier ID from allowed tiers list."""
    if not allowed_tiers:
        return "free-tier"
    for tier in allowed_tiers:
        if tier.get("isDefault"):
            return tier.get("id", "free-tier")
    return allowed_tiers[0].get("id", "free-tier") if allowed_tiers else "free-tier"


def onboard_managed_project(access_token: str, tier_id: str, attempts: int = 10, delay_sec: float = 5.0) -> str:
    """Onboard user and get the managed project ID."""
    import time
    
    url = "https://cloudcode-pa.googleapis.com/v1internal:onboardUser"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "google-api-nodejs-client/9.15.1",
        "X-Goog-Api-Client": "gl-node/22.17.0",
        "Client-Metadata": "ideType=IDE_UNSPECIFIED,platform=PLATFORM_UNSPECIFIED,pluginType=GEMINI",
    }
    payload = {
        "tierId": tier_id,
        "metadata": {
            "ideType": "IDE_UNSPECIFIED",
            "platform": "PLATFORM_UNSPECIFIED",
            "pluginType": "GEMINI",
        }
    }
    
    for attempt in range(attempts):
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if data.get("done"):
            project_id = data.get("response", {}).get("cloudaicompanionProject", {}).get("id", "")
            if project_id:
                return project_id
        
        if attempt < attempts - 1:
            time.sleep(delay_sec)
    
    return ""


def get_managed_project(access_token: str) -> str:
    """Call loadCodeAssist to get the managed project ID, onboarding if necessary."""
    url = "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "google-api-nodejs-client/9.15.1",
        "X-Goog-Api-Client": "gl-node/22.17.0",
        "Client-Metadata": "ideType=IDE_UNSPECIFIED,platform=PLATFORM_UNSPECIFIED,pluginType=GEMINI",
    }
    payload = {
        "metadata": {
            "ideType": "IDE_UNSPECIFIED",
            "platform": "PLATFORM_UNSPECIFIED",
            "pluginType": "GEMINI",
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    
    # If we already have a managed project, return it
    if data.get("cloudaicompanionProject"):
        return data["cloudaicompanionProject"]
    
    # Otherwise, we need to onboard the user first
    allowed_tiers = data.get("allowedTiers", [])
    tier_id = get_default_tier_id(allowed_tiers)
    
    return onboard_managed_project(access_token, tier_id)


def gemini_search(query: str, model: str = "gemini-2.5-flash") -> str:
    """
    Search using Gemini with Google Search grounding.

    Args:
        query: The search query or question to ask Gemini.
        model: The model to use (default: gemini-2.5-flash).

    Returns:
        The answer from Gemini along with source URLs.
    """
    try:
        # Step 1: Get the access token
        access_token = get_session()
    except FileNotFoundError as e:
        return str(e)

    # Step 2: Get managed project ID
    project_id = get_managed_project(access_token)

    # Step 3: Construct the payload
    payload = {
        "project": project_id,
        "model": model,
        "request": {
            "contents": [{"role": "user", "parts": [{"text": query}]}],
            "tools": [{"googleSearch": {}}],
        },
    }

    # Step 4: Send POST request
    url = f"{ENDPOINT}:generateContent"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "google-api-nodejs-client/9.15.1",
        "X-Goog-Api-Client": "gl-node/22.17.0",
        "Client-Metadata": "ideType=IDE_UNSPECIFIED,platform=PLATFORM_UNSPECIFIED,pluginType=GEMINI",
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Handle both HTTP errors and connection errors
        if hasattr(e, "response") and e.response is not None:
            return f"HTTP Error {e.response.status_code}: {e.response.text}"
        return f"Request failed: {e}"

    # Step 5: Parse Response
    try:
        data = response.json()
    except json.JSONDecodeError:
        return f"Failed to parse response as JSON: {response.text}"

    # The response might be wrapped
    if "response" in data:
        data = data["response"]

    # Extract answer text
    answer = ""
    try:
        candidates = data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                answer = parts[0].get("text", "")
    except (KeyError, IndexError):
        answer = "Unable to extract answer from response."

    # Extract grounding metadata (sources, supports, and search queries)
    sources = []
    grounding_supports = []
    web_search_queries = []
    
    try:
        candidates = data.get("candidates", [])
        if candidates:
            grounding_metadata = candidates[0].get("groundingMetadata", {})
            
            # Extract grounding chunks (sources)
            grounding_chunks = grounding_metadata.get("groundingChunks", [])
            for i, chunk in enumerate(grounding_chunks):
                web = chunk.get("web", {})
                uri = web.get("uri", "")
                title = web.get("title", "")
                if uri:
                    sources.append({"index": i + 1, "title": title, "uri": uri})
            
            # Extract grounding supports (citation mapping)
            # Structure: {"segment": {"startIndex": 0, "endIndex": 50}, 
            #             "groundingChunkIndices": [0, 1], "confidenceScores": [0.9, 0.8]}
            grounding_supports = grounding_metadata.get("groundingSupports", [])
            
            # Extract web search queries used by Gemini
            web_search_queries = grounding_metadata.get("webSearchQueries", [])
    except (KeyError, IndexError):
        pass

    # Step 6: Format and return result
    result = f"## Answer\n\n{answer}"
    
    # Format sources with numbered references
    if sources:
        result += "\n\n## Sources\n\n"
        for source in sources:
            title = source["title"] or "Untitled"
            result += f"[{source['index']}] {title} - {source['uri']}\n"
    
    # Format search queries used
    if web_search_queries:
        result += "\n## Search Queries Used\n\n"
        for query in web_search_queries:
            result += f"- {query}\n"
    
    # Format citation map (only if groundingSupports exists)
    if grounding_supports and answer:
        result += "\n## Citation Map\n\n"
        for support in grounding_supports:
            segment = support.get("segment", {})
            start_idx = segment.get("startIndex", 0)
            end_idx = segment.get("endIndex", 0)
            chunk_indices = support.get("groundingChunkIndices", [])
            confidence_scores = support.get("confidenceScores", [])
            
            # Extract the text segment from the answer
            text_segment = answer[start_idx:end_idx].strip()
            if text_segment and chunk_indices:
                # Truncate long segments for readability
                if len(text_segment) > 100:
                    text_segment = text_segment[:97] + "..."
                
                # Format source references (indices are 0-based, display as 1-based)
                source_refs = ", ".join(f"[{idx + 1}]" for idx in chunk_indices)
                
                # Format confidence scores as percentages
                if confidence_scores:
                    conf_strs = [f"{score * 100:.0f}%" for score in confidence_scores]
                    confidence_str = f" (confidence: {', '.join(conf_strs)})"
                else:
                    confidence_str = ""
                
                result += f'"{text_segment}" → Sources {source_refs}{confidence_str}\n\n'

    return result


# Register the callable as an MCP tool without replacing the function object.
# (Using `@mcp.tool()` would wrap the function and make it non-callable in tests.)
google_search_tool = mcp.tool(gemini_search, name="google_search")

def run_http(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run the MCP server in HTTP/SSE mode."""
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse").strip().lower()
    if transport == "stdio":
        mcp.run()
    else:
        run_http(
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "8080")),
        )
