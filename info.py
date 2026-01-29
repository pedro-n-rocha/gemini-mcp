#!/usr/bin/env python3
"""Display information about the current Gemini credentials and project."""

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import get_session, get_credentials_path

def get_user_info(access_token: str) -> dict:
    """Get user info from Google."""
    import requests
    response = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if response.ok:
        return response.json()
    return {}

def get_project_info(access_token: str) -> dict:
    """Get project and tier info from loadCodeAssist."""
    import requests
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
    if response.ok:
        return response.json()
    return {"error": response.text}

def main():
    print("=" * 60)
    print("Gemini Credentials Info")
    print("=" * 60)
    print()
    
    # Get access token
    try:
        access_token = get_session()
        print("✓ Credentials loaded successfully")
        creds_path = get_credentials_path()
        try:
            with open(creds_path, "r") as f:
                creds_data = json.load(f)
            expiry_raw = creds_data.get("expiry")
            if isinstance(expiry_raw, str) and expiry_raw:
                expiry = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00"))
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                remaining = (expiry - datetime.now(timezone.utc)).total_seconds()
                if remaining >= 0:
                    print(f"  Token expires at: {expiry.astimezone(timezone.utc).isoformat()}")
                    print(f"  Token TTL (approx): {int(remaining)}s")
                else:
                    print(f"  Token expiry: {expiry.astimezone(timezone.utc).isoformat()} (expired)")
        except Exception:
            # Best-effort: info still works without these fields
            pass
        print()
    except Exception as e:
        print(f"✗ Failed to load credentials: {e}")
        sys.exit(1)
    
    # Get user info
    print("## User Info")
    print("-" * 40)
    user_info = get_user_info(access_token)
    if user_info:
        print(f"  Email: {user_info.get('email', 'N/A')}")
        print(f"  Name: {user_info.get('name', 'N/A')}")
        print(f"  ID: {user_info.get('id', 'N/A')}")
    else:
        print("  Could not retrieve user info")
    print()
    
    # Get project info
    print("## Project & Tier Info")
    print("-" * 40)
    project_info = get_project_info(access_token)
    
    if "error" in project_info:
        print(f"  Error: {project_info['error']}")
    else:
        # Project
        project = project_info.get("cloudaicompanionProject", "Not assigned")
        print(f"  Managed Project: {project}")
        
        # Current tier
        current_tier = project_info.get("currentTier", {})
        print(f"  Current Tier ID: {current_tier.get('id', 'N/A')}")
        
        # Allowed tiers
        allowed_tiers = project_info.get("allowedTiers", [])
        if allowed_tiers:
            print()
            print("  Available Tiers:")
            for tier in allowed_tiers:
                tier_id = tier.get("id", "unknown")
                is_default = tier.get("isDefault", False)
                user_defined = tier.get("userDefinedCloudaicompanionProject", False)
                default_marker = " (default)" if is_default else ""
                user_marker = " [user-defined project]" if user_defined else ""
                print(f"    - {tier_id}{default_marker}{user_marker}")
    
    print()
    print("=" * 60)
    
    # Optional: dump raw JSON for debugging
    if len(sys.argv) > 1 and sys.argv[1] == "--raw":
        print()
        print("## Raw Response")
        print("-" * 40)
        print(json.dumps(project_info, indent=2))

if __name__ == "__main__":
    main()
