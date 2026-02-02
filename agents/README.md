# MiniDani Agents

Each agent is a specialized prompt that guides OpenCode for a specific task.

## Structure

```
agents/
├── README.md          # This file
├── manager.md         # Orchestrates implementation, delegates to blue/red team
├── blue-team.md       # Implementation specialist (subagent)
├── red-team.md        # Quality assurance specialist (subagent)
├── judge.md           # Evaluates and scores implementations
└── pr-creator.md      # Stages, commits, pushes, creates PR
```

## Agent Configuration

Each agent has YAML frontmatter defining model and behavior:

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
```

## Current Agents

| Agent | Mode | Model | Purpose |
|-------|------|-------|---------|
| **manager** | primary | claude-opus-4-5 | Orchestrates implementation, delegates to blue/red team |
| **blue-team** | subagent | gpt-5-codex | Implementation specialist, writes production code |
| **red-team** | subagent | gpt-5-codex | QA specialist, creates tests and validates |
| **judge** | primary | gpt-5-codex | Evaluates all 3 implementations, picks winner |
| **pr-creator** | primary | claude-opus-4-5 | Stages relevant files, commits, pushes, creates PR |

## How It Works

1. MiniDani calls OpenCode with `--agent <name>`
2. OpenCode loads the agent from `agents/<name>.md`
3. Agent frontmatter defines model, tools, permissions
4. Agent instructions guide the task execution

## Editing Agents

**Change model:**
Edit the `model:` field in the agent's frontmatter.

**Change behavior:**
Edit the markdown instructions below the frontmatter.

**Change tools:**
Edit the `tools:` section in frontmatter to enable/disable capabilities.

## Subagents vs Primary

- **primary**: Called directly by MiniDani (manager, judge, pr-creator)
- **subagent**: Called by manager via delegation (blue-team, red-team)

Subagents don't have timeouts in MiniDani - they run within the manager's timeout.
