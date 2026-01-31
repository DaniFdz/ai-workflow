#!/bin/bash
# Example: Complex task with MiniDani Retry

cd /path/to/your-project

python3 /path/to/minidani/minidani_retry.py \
  "Create a REST API for a blog with:
  - User authentication (JWT)
  - CRUD for posts (title, content, author, published_at)
  - CRUD for comments (linked to posts)
  - SQLite database with migrations
  - FastAPI or Flask
  - Pytest tests with >80% coverage
  - README with setup instructions
  - Docker setup (optional bonus)
  
  Create PR when done."

# Expected:
# - Round 1: 3 implementations (~3-5 min each)
# - Judge evaluates (expect high scores for this complexity)
# - If all < 80: Round 2 automatically starts
# - Winner selected, PR generated
# Time: ~5-15 minutes total
