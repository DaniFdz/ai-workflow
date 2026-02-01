# Model Configuration

MiniDani uses different models optimized for each task.

## Configuration File

**All agent configurations are in:** `.opencode/agents.json`

This file defines model + timeout for each agent. Edit it to customize:

```json
{
  "branch-namer": {
    "model": "openai/gpt-4o-mini",
    "timeout": 30
  },
  "manager": {
    "model": "anthropic/claude-opus-4-5",
    "timeout": 1800
  },
  ...
}
```

## Current Configuration

See `.opencode/agents.json` for the source of truth.

| Component | Default Model | Timeout | Reason |
|-----------|---------------|---------|--------|
| **Branch Namer** | `openai/gpt-4o-mini` | 30s | Fast & cheap for simple task |
| **Manager (A/B/C)** | `anthropic/claude-opus-4-5` | 1800s (30m) | High quality code generation |
| **Judge** | `anthropic/claude-opus-4-5` | 480s (8m) | Accurate evaluation |
| **PR Creator** | `anthropic/claude-opus-4-5` | 300s (5m) | Good documentation |
| **Red Team** | `openai/gpt-5-codex` | 1800s (30m) | Pure code (not yet implemented) |
| **Blue Team** | `anthropic/claude-opus-4-5` | 1200s (20m) | QA testing (not yet implemented) |

## Model Notes

- **Opus 4.5**: Best for complex reasoning, code quality, architecture
- **GPT-4o-mini**: Best for simple, fast tasks (branch names, summaries)
- **GPT-5-Codex**: Best for pure code generation (when available)

## Cost Comparison (approximate)

- Opus 4.5: ~$0.015/1K input, ~$0.075/1K output
- GPT-4o-mini: ~$0.00015/1K input, ~$0.0006/1K output
- Branch naming with mini vs Opus: **100x cheaper**

## Customization

To change a model or timeout, edit `.opencode/agents.json`:

```bash
# Use Sonnet instead of Opus for managers (cheaper)
jq '.manager.model = "anthropic/claude-sonnet-4-5"' .opencode/agents.json > tmp && mv tmp .opencode/agents.json

# Increase manager timeout to 40 minutes
jq '.manager.timeout = 2400' .opencode/agents.json > tmp && mv tmp .opencode/agents.json
```

Or edit directly in your favorite editor.
