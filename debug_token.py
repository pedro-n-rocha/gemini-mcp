#!/usr/bin/env python3
"""Debug script to check and refresh OAuth credentials."""

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Error: {CREDENTIALS_FILE} not found")
        return

    creds = Credentials.from_authorized_user_file(CREDENTIALS_FILE)

    # Print token expiry
    print(f"Token Expiry: {creds.expiry}")

    # Attempt to refresh the token
    try:
        creds.refresh(Request())
        print(f"Refresh Successful: {creds.token[:10]}")
    except Exception as e:
        print(f"Refresh Failed: {e}")


if __name__ == "__main__":
    main()
