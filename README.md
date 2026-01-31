# 🦞 MiniDani

**Competitive parallel AI development system**

MiniDani runs 3 AI coding agents in parallel competing to implement your feature, then automatically selects and merges the best solution.

---

## What is MiniDani?

MiniDani creates **competitive pressure** between AI agents to produce better code:

1. **Launch 3 Managers** (A, B, C) in parallel
2. Each manager independently implements your feature using [OpenCode](https://github.com/unit-mesh/opencode)
3. Each works in an isolated git worktree
4. A **Judge** evaluates all 3 implementations (0-100 score)
5. Winner is kept, losers are cleaned up
6. PR description is auto-generated

**Smart retry:** If all scores < 80, MiniDani automatically runs Round 2 with improvement feedback.

---

## Quick Start

### Requirements

```bash
pip install -r requirements.txt
```

**Dependencies:**
- Python 3.8+
- Git
- [OpenCode CLI](https://github.com/unit-mesh/opencode) installed at `~/.opencode/bin/opencode`
- Rich library (for TUI, auto-installed via requirements.txt)

### Usage

```bash
cd /path/to/your/project
python3 /path/to/minidani.py "Add OAuth2 authentication with JWT tokens"
```

**What happens:**
- 3 parallel implementations start immediately
- Live TUI shows progress (phases, managers, scores, activity log)
- After 5-10 minutes, you have the best solution auto-selected
- Winner branch is ready for PR

---

## How It Works

### Architecture

![MiniDani Workflow](assets/workflow-diagram.png)

**6-Phase Process:**

```
User Prompt
    ↓
[Phase 1] Generate branch name → feature/oauth-auth
    ↓
[Phase 2] Create 3 git worktrees (isolated workspaces)
    ↓
[Phase 3] Run 3 Managers in parallel threads:
          Manager A: feature/oauth-auth-r1-a
          Manager B: feature/oauth-auth-r1-b  
          Manager C: feature/oauth-auth-r1-c
    ↓
[Phase 4] Judge evaluates all 3:
          A=87, B=95, C=82 → Winner: B
    ↓
[Phase 5] Cleanup: Delete worktrees A and C
    ↓
[Phase 6] Generate PR description from winner
    ↓
✅ Ready to merge feature/oauth-auth-r1-b
```

### Retry Logic (Automatic Quality Assurance)

If **all** scores are below 80:
- Round 2 launches automatically
- Managers get feedback about Round 1 failures
- Focus on: complete implementation, tests, docs, error handling
- Best solution from either round wins

Example:
```
Round 1: A=45, B=50, C=40  ⚠️  Low quality detected
         ↓
Round 2: A=85, B=88, C=82  ✅ Winner: B (88/100)
```

---

## Judging Criteria

Judges evaluate on 4 dimensions:

| Criterion | Weight | What it measures |
|-----------|--------|------------------|
| **Completeness** | 35% | Implements all requirements? |
| **Code Quality** | 30% | Clean, maintainable, readable? |
| **Correctness** | 25% | Works correctly, handles edge cases? |
| **Best Practices** | 10% | Tests, docs, error handling? |

**Scoring guide:**
- **90-100**: Excellent - complete, tested, documented
- **80-89**: Good - functional with minor issues
- **70-79**: Acceptable - works but needs polish
- **<70**: Insufficient - missing features or broken

---

## Live TUI Interface

While running, you see:

```
┌─────────────────────────────────────────────┐
│ 🦞 MiniDani [Round 1]                      │
│ feature/oauth-auth | 00:04:32               │
└─────────────────────────────────────────────┘

┌─ Phases ──────────┐  ┌─ Managers (Round 1) ──────────┐
│ ✅ 1. Branch  100%│  │ 🤖 Manager A                   │
│ ✅ 2. Setup   100%│  │    🔄 running (i3)             │
│ 🔄 3. Managers 67%│  │    Implementing auth logic     │
│ ⏳ 4. Judge     0%│  │                                │
│ ⏳ 5. Cleanup   0%│  │ 🤖 Manager B                   │
│ ⏳ 6. PR        0%│  │    🔄 running (i4)             │
└───────────────────┘  │    Writing tests               │
                        │    🏆 Score: 88/100            │
                        │                                │
                        │ 🤖 Manager C                   │
                        │    ✅ complete (i2)            │
                        │    Done                        │
                        │    Score: 75/100               │
                        └────────────────────────────────┘
                        
┌─ Activity Log ────────────────────────────────┐
│ 18:22:15 [MA] 🔄 Start R1                    │
│ 18:22:17 [MB] 🔄 Start R1                    │
│ 18:22:19 [MC] 🔄 Start R1                    │
│ 18:25:42 [MC] ✅ OK R1                       │
│ 18:26:35 [MA] ✅ OK R1                       │
│ 18:27:18 [MB] ✅ OK R1                       │
│ 18:27:20 [Judge] ⚖️ Scores R1: A=87,B=88,C=75│
│ 18:27:21 [Judge] 🏆 Winner: B                │
└───────────────────────────────────────────────┘

 🏆 Winner: B
```

---

## Configuration

### Quality Threshold

Edit `minidani.py`:

```python
self.QUALITY_THRESHOLD = 80  # Change to 70 or 90
```

### Timeouts

```python
# Manager execution timeout (default: 8 minutes per manager)
r = self.run_oc(..., timeout=480)

# Judge timeout (default: 2 minutes)
r = self.run_oc(..., timeout=120)
```

---

## Project Structure

```
minidani/
├── minidani.py              # Main script (TUI + retry logic)
├── requirements.txt         # Python dependencies (rich)
├── INSTALL.md              # Installation guide
├── README.md               # This file
├── LICENSE                 # MIT license
│
├── .opencode/              # OpenCode agent templates (reference)
│   ├── agents/             # Agent definitions (not directly used)
│   └── skills/             # Skills (for future extensions)
│
├── docs/
│   ├── ARCHITECTURE.md     # Technical design
│   └── QUICKSTART.md       # 5-minute guide
│
└── examples/
    ├── simple-task.sh      # Example: simple feature
    └── complex-task.sh     # Example: complex feature
```

**Note:** The `.opencode/agents/*.md` files are **reference templates** showing how a multi-agent system could be structured. The actual implementation directly calls OpenCode with custom prompts (see `minidani.py`).

---

## Examples

### Simple Task

```bash
python3 minidani.py "Create a function to validate email addresses with regex"
```

**Result:** 3 implementations compete, best one selected in ~2 minutes.

### Complex Task

```bash
python3 minidani.py "Build a REST API with:
- User authentication (JWT)
- CRUD operations for posts
- SQLite database
- Pytest test suite
- Docker setup"
```

**Result:** 3 full implementations compete, best one selected in ~10 minutes.

### With Retry

```bash
python3 minidani.py "Hello world script"
```

**Result:**
```
Round 1: A=45, B=50, C=40  ⚠️  Too simple, low scores
Round 2: A=85, B=88, C=82  ✅ Improved with feedback
Winner: B (88/100)
```

---

## Troubleshooting

### OpenCode not found

```bash
# Check installation
ls -la ~/.opencode/bin/opencode

# Add to PATH if needed
export PATH="$HOME/.opencode/bin:$PATH"
```

### Worktree conflicts

```bash
# List worktrees
git worktree list

# Remove stuck worktree
git worktree remove /path/to/worktree --force

# Remove branch
git branch -D feature/name-r1-a
```

### All scores below 50

**Causes:**
- Prompt too simple (judge expects more)
- Prompt ambiguous (managers confused)
- OpenCode having issues

**Solution:** MiniDani will auto-retry. If Round 2 also fails, check OpenCode logs.

---

## Advanced Usage

### Custom Repository Path

Edit `minidani.py`:

```python
if __name__ == "__main__":
    # Change from /tmp/minidani-test-repo to your repo
    minidani = MiniDaniRetry(
        Path("/path/to/your/repo"),
        " ".join(sys.argv[1:])
    )
```

### Run Without TUI (headless)

Comment out the `with Live(...)` block and use plain print statements.

### Customize Manager Count

Currently hardcoded to 3 (A, B, C). To change:

1. Edit `self.state.managers = {...}` in `__init__`
2. Update all loops: `for m in ["a","b","c"]` → `for m in ["a","b","c","d"]`
3. Update Phase 2 setup and cleanup logic

---

## How Is This Different?

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **Single AI** | One agent implements | Fast | Limited quality |
| **Iterative refinement** | Agent + feedback loop | Improved quality | Time-consuming |
| **MiniDani** | 3 parallel + judge | Best quality, same time | Uses 3x compute |

**MiniDani's advantage:** Competitive pressure + parallel execution = better results in the same time as a single refined attempt.

---

## Limitations

- **OpenCode dependency:** Requires OpenCode CLI installed and working
- **Compute cost:** Runs 3 instances in parallel (3x API calls)
- **Git worktrees:** Requires clean git state, no conflicts
- **No LangChain/Autogen:** Direct OpenCode subprocess calls (simpler, more reliable)

---

## Future Ideas

- [ ] Support 5+ managers
- [ ] Web UI instead of terminal TUI
- [ ] Support other AI coding tools (Aider, Cursor, Claude Code)
- [ ] Persistent judging database (learn what "good" means)
- [ ] Team mode (Red team implements, Blue team reviews)
- [ ] Streaming logs from OpenCode in real-time

---

## Contributing

Improvements welcome:

1. Fork the repo
2. Create branch: `git checkout -b feature/improvement`
3. Test with multiple tasks
4. Create PR with clear description

---

## License

MIT License - Use freely, improve, share.

---

## Credits

- **[OpenCode](https://github.com/unit-mesh/opencode)** - AI coding tool powering each manager
- **[Rich](https://github.com/Textualize/rich)** - Beautiful TUI library
- **Claude/Anthropic** - AI model behind OpenCode

---

## Contact

- **Issues:** [GitHub Issues](https://github.com/DaniFdz/ai-workflow/issues)
- **Discussions:** [GitHub Discussions](https://github.com/DaniFdz/ai-workflow/discussions)

---

**Version:** 1.0.0  
**Last updated:** 2026-01-31  
**Author:** DaniFdz (with help from JuanBot 🦞)
