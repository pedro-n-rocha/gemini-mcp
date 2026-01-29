#!/usr/bin/env python3
"""Manual OAuth2 authentication for Gemini CLI MCP."""

import requests
import hashlib
import base64
import os
import json
import urllib.parse
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

# OAuth app credentials (do not hardcode these in the repo).
# Provide them via environment variables:
#   - GOOGLE_OAUTH_CLIENT_ID
#   - GOOGLE_OAUTH_CLIENT_SECRET
load_dotenv()
CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8085/oauth2callback"
SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# OAuth2 endpoints
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

def require_oauth_app_credentials() -> tuple[str, str]:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "Missing OAuth app credentials. Set GOOGLE_OAUTH_CLIENT_ID and "
            "GOOGLE_OAUTH_CLIENT_SECRET environment variables."
        )
    return CLIENT_ID, CLIENT_SECRET


def generate_pkce():
    """Generate PKCE code verifier and challenge."""
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=')
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier).digest()
    ).rstrip(b'=')
    return verifier.decode('ascii'), challenge.decode('ascii')


def build_auth_url(code_challenge: str, code_verifier: str) -> str:
    """Build the OAuth2 authorization URL."""
    client_id, _client_secret = require_oauth_app_credentials()
    # Create state object with verifier (like the plugin does)
    state_obj = {"verifier": code_verifier}
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_obj).encode()).decode().rstrip('=')
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
        "state": encoded_state,
    }
    # Append hash fragment like the plugin does
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}#opencode"


def exchange_code_for_tokens(code: str, code_verifier: str) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    client_id, client_secret = require_oauth_app_credentials()
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    
    response = requests.post(TOKEN_URL, data=data)
    response.raise_for_status()
    return response.json()


def save_credentials(tokens: dict):
    """Save tokens to credentials file."""
    # Use CREDENTIALS_PATH env var if set, otherwise fall back to script directory
    filepath = os.environ.get("CREDENTIALS_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json"))
    client_id, client_secret = require_oauth_app_credentials()

    obtained_at = datetime.now(timezone.utc)
    expires_in = tokens.get("expires_in")
    expiry = None
    if isinstance(expires_in, (int, float)):
        expiry = obtained_at + timedelta(seconds=float(expires_in))
    
    credentials = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type"),
        "expires_in": tokens.get("expires_in"),
        "obtained_at": obtained_at.isoformat(),
        "expiry": expiry.isoformat() if expiry else None,
        "scope": tokens.get("scope"),
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    with open(filepath, "w") as f:
        json.dump(credentials, f, indent=2)
    
    print(f"Credentials saved to {filepath}")


def extract_code_from_url(url: str) -> str:
    """Extract the code parameter from a redirect URL."""
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    if "code" in params:
        return params["code"][0]
    raise ValueError("No 'code' parameter found in URL")


def main():
    """Main authentication flow."""
    print("=" * 60)
    print("Gemini CLI OAuth2 Manual Authentication")
    print("=" * 60)
    print()

    try:
        require_oauth_app_credentials()
    except RuntimeError as e:
        print(f"Error: {e}")
        print()
        print("Example:")
        print("  export GOOGLE_OAUTH_CLIENT_ID='...apps.googleusercontent.com'")
        print("  export GOOGLE_OAUTH_CLIENT_SECRET='...'\n")
        raise

    # Generate PKCE
    code_verifier, code_challenge = generate_pkce()
    
    # Build and display auth URL
    auth_url = build_auth_url(code_challenge, code_verifier)
    print("Visit this URL in your browser:")
    print()
    print(auth_url)
    print()
    print("-" * 60)
    print("After logging in, you will be redirected to localhost:8085.")
    print("The page may fail to load - that's OK!")
    print()
    print("Copy the FULL URL from your browser's address bar")
    print("(or just the 'code' parameter value) and paste it below:")
    print("-" * 60)
    print()
    
    user_input = input("Paste URL or code here: ").strip()
    
    # Extract code from input
    if user_input.startswith("http"):
        code = extract_code_from_url(user_input)
    else:
        code = user_input
    
    print()
    print("Exchanging code for tokens...")
    
    try:
        tokens = exchange_code_for_tokens(code, code_verifier)
        save_credentials(tokens)
        print()
        print("=" * 60)
        print("SUCCESS! Authentication complete.")
        print("=" * 60)
    except requests.exceptions.HTTPError as e:
        print(f"Error exchanging code: {e}")
        print(f"Response: {e.response.text}")
        raise


if __name__ == "__main__":
    main()
