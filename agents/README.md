# MiniDani Agents

Each agent is a specialized prompt that guides the AI model for a specific task.

## Structure

```
agents/
├── README.md          # This file
├── branch-namer.md    # Branch naming agent prompt
├── manager.md         # (TODO) Manager orchestration prompt
├── judge.md           # (TODO) Evaluation and scoring prompt
├── pr-creator.md      # (TODO) PR description generator
├── red-team.md        # (TODO) Code generation specialist
└── blue-team.md       # (TODO) Quality assurance specialist

../agents.json         # Model + timeout configuration per agent
```

## Configuration

**All agent configurations are in:** `agents.json` (project root)

```json
{
  "branch-namer": {
    "model": "openai/gpt-4o-mini",
    "timeout": 30
  },
  "manager": {
    "model": "anthropic/claude-opus-4-5",
    "timeout": 1800
  }
}
```

## Current Agents

| Agent | Purpose | Model | Status |
|-------|---------|-------|--------|
| **branch-namer** | Generate branch names | gpt-4o-mini | ✅ Implemented |
| **manager** | Orchestrate implementation | claude-opus-4-5 | 📝 Uses inline prompt |
| **judge** | Evaluate implementations | claude-opus-4-5 | 📝 Uses inline prompt |
| **pr-creator** | Generate PR descriptions | claude-opus-4-5 | 📝 Uses inline prompt |
| **red-team** | Code generation | gpt-5-codex | ❌ Not implemented |
| **blue-team** | Quality assurance | claude-opus-4-5 | ❌ Not implemented |

## How It Works

1. When MiniDani calls an agent (e.g., `agent="branch-namer"`):
   - Loads `agents/<agent>.md` as system prompt (if exists)
   - Loads model + timeout from `agents.json`
   - Prepends agent instructions to user prompt
   - Calls OpenCode with configured model

2. Agent prompt structure:
   ```markdown
   # Agent Name
   
   You are a specialized agent for [task].
   
   ## Rules
   - Rule 1
   - Rule 2
   
   ## Examples
   Input: ...
   Output: ...
   
   ## Your Task
   [User prompt will be appended here]
   ```

## Creating a New Agent

1. **Create the prompt file:**
   ```bash
   cat > agents/my-agent.md << 'EOF'
   # My Agent
   
   You are a specialized agent for [specific task].
   
   ## Rules
   - Be concise
   - Output only [specific format]
   
   ## Your Task
   [User prompt appended here]
   EOF
   ```

2. **Add to agents.json:**
   ```json
   {
     "my-agent": {
       "model": "anthropic/claude-opus-4-5",
       "timeout": 300,
       "description": "What this agent does"
     }
   }
   ```

3. **Use in code:**
   ```python
   result, error = self.run_oc(prompt, context, agent="my-agent")
   ```

## Best Practices

- ✅ **Clear, specific instructions** - No ambiguity
- ✅ **Output format examples** - Show exactly what you want
- ✅ **Concise prompts** - Shorter = faster + cheaper
- ✅ **Right model for task** - Fast models for simple tasks, powerful for complex
- ✅ **Reasonable timeouts** - 30s for simple, 30m for complex

## Customization

**Change a model:**
```bash
jq '.manager.model = "anthropic/claude-sonnet-4-5"' agents.json > tmp && mv tmp agents.json
```

**Increase timeout:**
```bash
jq '.judge.timeout = 600' agents.json > tmp && mv tmp agents.json
```
