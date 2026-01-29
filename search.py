#!/usr/bin/env python3
"""CLI script to search with Gemini."""

import sys
import os

# Add parent directory to path so we can import server
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import gemini_search

def main():
    if len(sys.argv) < 2:
        print("Usage: python search.py <query> [model]")
        print("Example: python search.py 'What is the latest news on AI?'")
        print("Example: python search.py 'What is Bitcoin price?' gemini-2.5-pro")
        sys.exit(1)
    
    query = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "gemini-2.5-flash"
    
    print(f"Searching with {model}...\n")
    result = gemini_search(query, model=model)
    print(result)

if __name__ == "__main__":
    main()
