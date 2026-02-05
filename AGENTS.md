# AGENTS.md - Guide for AI Agents

This file helps AI coding agents understand and work on the MiniDani codebase.

## Project Overview

**MiniDani** is a competitive parallel AI development system that runs 3 AI coding agents in parallel, then a judge selects the best implementation.

## Architecture

```
minidani.py          # Main CLI and orchestration logic
pi_client.py         # RPC client for pi coding agent
check_pi.py          # Installation verification script
generate_branch_name.py  # Branch name generation (uses OpenAI API)
agents/              # Agent prompts (reference documentation)
├── manager.md       # Orchestrates implementation (delegates to blue/red team)
├── blue-team.md     # Implementation specialist (subagent)
├── red-team.md      # Quality assurance specialist (subagent)
├── judge.md         # Evaluates and scores implementations
└── pr-creator.md    # Stages, commits, pushes, creates PR
```

## Key Components

### minidani.py

Main entry point. Key classes:
- `ManagerState` - Tracks each manager's progress (a, b, c)
- `SystemState` - Global state (prompt, phases, winner, etc.)
- `MiniDaniRetry` - Main orchestration class

**6-Phase workflow:**
1. `p1_branch()` - Generate branch name
2. `p2_setup()` - Create git worktrees for each manager
3. `p3_managers()` - Run 3 managers in parallel (using pi coding agent)
4. `p4_judge()` - Judge evaluates all implementations
5. `p5_cleanup()` - Remove losing worktrees
6. `p6_pr()` - Create PR (or local commit with --no-pr)

**Important methods:**
- `run_pi(prompt, cwd, agent)` - Calls pi coding agent via RPC
- `run_manager(mid, round_num)` - Runs a single manager
- `cleanup_all_worktrees()` - Cleanup on exit/error (includes pi process cleanup)

### Agent System

Agents are markdown files in `agents/` with YAML frontmatter:

```yaml
---
description: What this agent does
mode: primary|subagent
model: provider/model-name
temperature: 0.3
tools:
  write: true
  edit: true
  bash: true
---

# Agent Instructions
...
```

**Current agents:**
| Agent | Mode | Model | Purpose |
|-------|------|-------|---------|
| manager | primary | claude-opus-4-5 | Orchestrates, delegates to blue/red team |
| blue-team | subagent | gpt-5-codex | Implements code |
| red-team | subagent | gpt-5-codex | Tests and QA |
| judge | primary | gpt-5-codex | Scores implementations |
| pr-creator | primary | claude-opus-4-5 | Stages, commits, pushes, creates PR |

### Pi Coding Agent Integration

MiniDani uses [pi-mono](https://github.com/badlogic/pi-mono) coding agent via RPC mode for programmatic control.

**Why Pi?**
- **Lower memory footprint**: ~50-100MB vs ~200-300MB per agent
- **Programmatic control**: Full RPC protocol for state management
- **Extensibility**: TypeScript extensions without forking
- **Aligned philosophy**: Minimal, explicit, observable

**RPC Mode:**
```bash
# Start pi in RPC mode
pi --rpc --model claude-sonnet-4-5 --non-interactive
```

**Communication Protocol:**
- JSON line-delimited over stdin/stdout
- Event types: `text`, `tool_call`, `tool_result`, `completion`, `error`
- See `pi_client.py` for full implementation

Install: `npm install -g @mariozechner/pi-coding-agent`

## Making Changes

### Adding a new agent

1. Create `agents/new-agent.md` with frontmatter
2. Use in code: `run_pi(prompt, cwd, agent="new-agent")`

### Modifying workflow

- Phases are in `p1_*` through `p6_*` methods
- Parallel execution in `p3_managers()` uses threading
- Judge scoring in `p4_judge()` parses JSON response

### Changing models/timeouts

- Models: Edit YAML frontmatter in `agents/*.md`
- Timeouts: Only manager has timeout in `self.agent_timeouts`

## CLI Flags

| Flag | Description |
|------|-------------|
| `-n, --no-pr` | Commit locally, don't create PR |
| `-b, --branch-name` | Specify branch name manually |
| `-f, --file` | Read prompt from file |
| `--branch-prefix` | Add prefix to branch (e.g., "feat/") |

## Testing Changes

```bash
# Create test repo
cd /tmp && mkdir test && cd test
git init && echo "# Test" > README.md && git add . && git commit -m "init"

# Run
minidani -n "Create hello.py that prints Hello World"

# Check result
git log --oneline -1
cat hello.py
```

## Common Issues

1. **Pi coding agent not found** - Install with `npm install -g @mariozechner/pi-coding-agent`
2. **Worktree conflicts** - Run `git worktree prune` in repo
3. **Agent not found** - Check `agents/<name>.md` exists with valid frontmatter

## Code Style

- Python 3.8+
- No Spanish in code or comments (English only)
- Concise logging via `self.log()`
- Use `subprocess.run()` for shell commands
