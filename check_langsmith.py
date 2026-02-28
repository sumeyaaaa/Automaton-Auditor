#!/usr/bin/env python3
"""Quick script to check LangSmith configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

tracing = os.getenv("LANGCHAIN_TRACING_V2", "")
api_key = os.getenv("LANGCHAIN_API_KEY", "")
project = os.getenv("LANGCHAIN_PROJECT", "Not Set")

print("=" * 50)
print("LangSmith Configuration Check")
print("=" * 50)
print(f"LANGCHAIN_TRACING_V2: {tracing}")
print(f"LANGCHAIN_API_KEY: {'[SET]' if api_key else '[NOT SET]'} ({len(api_key)} chars)")
print(f"LANGCHAIN_PROJECT: {project}")
print("=" * 50)

if tracing.lower() == "true" and api_key:
    print("[OK] LangSmith tracing is configured correctly!")
    print("\nTo get your trace link:")
    print("1. Run an audit: python -m src.graph <repo_url> <pdf_path>")
    print("2. Go to: https://smith.langchain.com")
    print("3. Navigate to Projects -> automaton-auditor")
    print("4. Click on the latest run to get the trace URL")
else:
    print("[ERROR] LangSmith tracing is NOT configured!")
    print("\nTo set it up:")
    print("1. Get API key from: https://smith.langchain.com → Settings → API Keys")
    print("2. Add to .env file:")
    print("   LANGCHAIN_TRACING_V2=true")
    print("   LANGCHAIN_API_KEY=lsv2_pt_your_key_here")
    print("   LANGCHAIN_PROJECT=automaton-auditor")

