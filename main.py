#!/usr/bin/env python3
"""Gemini MCP container main.

This container always starts the MCP server in HTTP/SSE mode.
If credentials are missing, it runs the interactive OAuth flow,
prints credential/project info, then starts the server.
"""

from __future__ import annotations

import os


def ensure_credentials(credentials_path: str) -> None:
    if os.path.exists(credentials_path):
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
    credentials_path = os.environ.get("CREDENTIALS_PATH", "/app/config/credentials.json")
    ensure_credentials(credentials_path)
    print_info()

    from server import run_http

    run_http(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
    )


if __name__ == "__main__":
    main()

