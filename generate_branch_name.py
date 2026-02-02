#!/usr/bin/env python3
"""
Simple branch name generator using OpenAI gpt-4o-mini
Returns JSON: {"branch_name": "feat/branch-name"}
"""

import os
import sys
import json
from openai import OpenAI

SYSTEM_PROMPT = """You generate concise, semantic git branch names WITHOUT any prefix.

Rules:
1. Output ONLY valid JSON: {"branch_name": "your-branch-name"}
2. Use kebab-case (lowercase with hyphens)
3. 2-4 words maximum
4. NEVER include prefixes like feat/, fix/, etc. - only the descriptive part
5. No quotes around the branch name in the output

Examples:
- Input: "Add OAuth2 authentication" → {"branch_name": "oauth-auth"}
- Input: "Fix bug in login" → {"branch_name": "login-bug"}
- Input: "Create REST API for users" → {"branch_name": "create-user-api"}
- Input: "Refactor database connection pooling" → {"branch_name": "refactor-db-pool"}

The prefix will be added by the caller, don't include it.
"""

def generate_branch_name(task_description: str) -> dict:
    """
    Generate a branch name using OpenAI API (without prefix)
    
    Args:
        task_description: Description of the task
    
    Returns:
        dict: {"branch_name": "descriptive-name"} (without prefix)
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Task: {task_description}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=50
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        # Fallback to simple generation
        return {"branch_name": "task"}

def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate git branch name (descriptive part only, no prefix)")
    parser.add_argument("task", help="Task description")
    
    args = parser.parse_args()
    
    result = generate_branch_name(args.task)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
