#!/usr/bin/env python3
"""
Simple branch name generator using OpenAI gpt-4o-mini
Returns JSON: {"branch_name": "feat/branch-name"}
"""

import os
import sys
import json
from openai import OpenAI

SYSTEM_PROMPT = """You generate concise, semantic git branch names.

Rules:
1. Output ONLY valid JSON: {"branch_name": "your-branch-name"}
2. Use kebab-case (lowercase with hyphens)
3. 2-4 words maximum
4. Include prefix if provided in user prompt
5. No quotes around the branch name in the output

Examples:
- Input: "Add OAuth2 authentication" → {"branch_name": "oauth-auth"}
- Input: "Fix bug in login" → {"branch_name": "fix-login-bug"}
- Input: "Prefix: feat/ Task: Create REST API" → {"branch_name": "feat/create-api"}
"""

def generate_branch_name(task_description: str, prefix: str = "") -> dict:
    """
    Generate a branch name using OpenAI API
    
    Args:
        task_description: Description of the task
        prefix: Optional branch prefix (e.g., "feat/", "fix/")
    
    Returns:
        dict: {"branch_name": "generated-name"}
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Build user prompt
    if prefix:
        user_prompt = f"Branch prefix: {prefix}\nTask: {task_description}"
    else:
        user_prompt = f"Task: {task_description}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=50
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        # Fallback to simple generation
        return {"branch_name": f"{prefix}task" if prefix else "task"}

def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate git branch name")
    parser.add_argument("task", help="Task description")
    parser.add_argument("--prefix", default="", help="Branch prefix (e.g., feat/, fix/)")
    
    args = parser.parse_args()
    
    result = generate_branch_name(args.task, args.prefix)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
