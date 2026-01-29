#!/usr/bin/env python3
"""Gemini MCP container main.

This container always starts the MCP server in HTTP/SSE mode.
If credentials are missing, it runs the interactive OAuth flow,
prints credential/project info, then starts the server.
"""

from __future__ import annotations

import os


def ensure_credentials(credentials_path: str) -> None:
    if os.path.isfile(credentials_path):
        return

    print("=" * 60)
    print("NO CREDENTIALS FOUND")
    print("=" * 60)
    print(f"Expected credentials at: {credentials_path}")
    print()
    print("Starting interactive OAuth flow now...")
    print("=" * 60)
    print()

    import manual_auth

    manual_auth.main()


def print_info() -> None:
    import info

    info.main()


def main() -> None:
    creds_dir = (os.environ.get("CREDENTIALS_PATH") or "").strip()
    if not creds_dir:
        creds_dir = os.path.dirname(os.path.abspath(__file__))
    creds_dir = os.path.expanduser(creds_dir)
    if creds_dir.lower().endswith(".json"):
        raise ValueError(f"CREDENTIALS_PATH must be a directory, not a file path: {creds_dir}")
    credentials_path = os.path.join(creds_dir, "credentials.json")
    ensure_credentials(credentials_path)
    print_info()

    from server import run_http

    run_http(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("HTTP_PORT") or os.environ.get("PORT", "8080")),
    )


if __name__ == "__main__":
    main()
