# Model Configuration

MiniDani uses different models optimized for each task:

## Current Configuration

| Component | Model | Reason |
|-----------|-------|--------|
| **Branch Namer** | `openai/gpt-4o-mini` | Fast & cheap for simple task (~5-10s) |
| **Manager (A/B/C)** | `anthropic/claude-opus-4-5` | High quality code generation (default) |
| **Judge** | `anthropic/claude-opus-4-5` | Accurate evaluation (default) |
| **PR Creator** | `anthropic/claude-opus-4-5` | Good documentation (default) |

## Planned

| Component | Model | Status |
|-----------|-------|--------|
| **Red Team** | `openai/gpt-5-codex` | Not yet implemented |

## Performance Notes

- **Opus 4.5**: Best for complex reasoning, code quality, architecture
- **GPT-4o-mini**: Best for simple, fast tasks (branch names, summaries)
- **GPT-5-Codex**: Best for pure code generation (when available)

## Cost Comparison (approximate)

- Opus 4.5: ~$0.015/1K input, ~$0.075/1K output
- GPT-4o-mini: ~$0.00015/1K input, ~$0.0006/1K output
- Branch naming with mini vs Opus: **100x cheaper**

## Timeout Configuration

- Branch namer: 30s (fast model)
- Manager: 1800s / 30 min (needs time for iterations)
- Judge: 480s / 8 min (evaluation + scoring)
