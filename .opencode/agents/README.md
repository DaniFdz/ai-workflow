# MiniDani Agents

Each agent is a specialized prompt that guides the AI model for a specific task.

## Agent Files

- **`<agent-name>.md`** - Markdown file with agent instructions (system prompt)
- **Configuration in `../agents.json`** - Model + timeout per agent

## How It Works

1. When MiniDani calls an agent (e.g., `agent="branch-namer"`):
   - Loads `branch-namer.md` as system prompt
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

## Current Agents

| Agent | Purpose | Model | File |
|-------|---------|-------|------|
| **branch-namer** | Generate concise branch names | gpt-4o-mini | `branch-namer.md` |
| **manager** | Coordinate full implementation | claude-opus-4-5 | `manager.md` (TODO) |
| **judge** | Evaluate and score implementations | claude-opus-4-5 | `judge.md` (TODO) |
| **pr-creator** | Generate PR descriptions | claude-opus-4-5 | `pr-creator.md` (TODO) |
| **red-team** | Code generation specialist | gpt-5-codex | `red-team.md` (TODO) |
| **blue-team** | Quality assurance | claude-opus-4-5 | `blue-team.md` (TODO) |

## Creating a New Agent

1. **Create the prompt file:**
   ```bash
   cat > .opencode/agents/my-agent.md << 'EOF'
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

## Troubleshooting

**Agent not found:**
- Check file exists: `.opencode/agents/<name>.md`
- Check entry in `agents.json`

**Wrong model used:**
- Verify `agents.json` has correct model
- Check for hardcoded model overrides in code

**Timeout issues:**
- Increase timeout in `agents.json`
- Use faster model for simple tasks
- Simplify agent instructions
