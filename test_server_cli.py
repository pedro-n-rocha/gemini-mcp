#!/usr/bin/env python3
"""Test script for gemini_search function."""

from server import gemini_search

def main() -> None:
    result = gemini_search("Hello, are you working?", model="gemini-2.5-flash")
    print(result)


if __name__ == "__main__":
    main()
