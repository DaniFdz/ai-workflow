# 🦞 MiniDani

**Competitive parallel AI development system**

MiniDani runs 3 AI coding agents in parallel competing to implement your feature, then automatically selects and merges the best solution.

---

## Table of Contents

- [What is MiniDani?](#what-is-minidani)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [How It Works](#how-it-works)
- [Judging Criteria](#judging-criteria)
- [Live TUI Interface](#live-tui-interface)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)
- [How Is This Different?](#how-is-this-different)
- [Contributing](#contributing)
- [License](#license)

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

[↑ Back to top](#table-of-contents)

---

## Quick Start

### Basic Usage

```bash
# 1. Install (one-time setup)
./install.sh

# 2. Run from any project directory
cd /path/to/your/project

# Inline prompt (short tasks)
minidani "Add OAuth2 authentication with JWT tokens"
```

### Using a Prompt File

For complex prompts, save to a file and use `-f`:

```bash
# Create a prompt file
cat > prompt.md << 'EOF'
Build a REST API with the following features:

- User authentication using JWT tokens
- CRUD operations for posts (create, read, update, delete)
- SQLite database with proper migrations
- Comprehensive test suite using pytest
- Docker setup with docker-compose
- API documentation with OpenAPI/Swagger
- Rate limiting middleware
- Input validation and error handling

Technical requirements:
- Python 3.8+
- FastAPI or Flask
- SQLAlchemy ORM
- Follow PEP 8 style guide
- 80%+ test coverage
EOF

# Option 1: Read from file (recommended)
minidani -f prompt.md

# Option 2: Pipe stdin
cat prompt.md | minidani

# Option 3: Redirect stdin
minidani < prompt.md
```

**What happens:**
- 3 parallel implementations start immediately
- Live TUI shows progress (phases, managers, scores, activity log)
- After 30-40 minutes, you have the best solution auto-selected
- Winner branch is ready for PR

[↑ Back to top](#table-of-contents)

---

## Installation

### Prerequisites

- **Python 3.8+**
- **OpenCode CLI** - Install from [OpenCode](https://github.com/unit-mesh/opencode)

### Automatic Installation (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/DaniFdz/ai-workflow/master/install.sh | bash
```

This will:
- ✅ Verify Python 3.8+ is installed
- ✅ Create a virtual environment with dependencies
- ✅ Install `minidani` command in your PATH
- ✅ Make it available system-wide

After installation:
```bash
cd /path/to/your/project
minidani "Your task here"
```

### Manual Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/DaniFdz/ai-workflow.git
   cd ai-workflow
   ```

2. **Run the installer**
   ```bash
   ./install.sh
   ```

   Or install dependencies manually:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

### Verify Installation

```bash
# Test OpenCode
opencode --version

# Test MiniDani command
minidani --help 2>/dev/null || echo "Run 'minidani' from any directory"

# Test with a simple task (creates temporary test repo)
cd /tmp
mkdir test-minidani && cd test-minidani
git init
echo "# Test" > README.md
git add . && git commit -m "init"
minidani "Create hello.py that prints hello world"
```

[↑ Back to top](#table-of-contents)

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

**Agent System:** MiniDani uses 6 specialized agents in `.opencode/agents/`:
- `branch-namer.md` - Phase 1: Generate semantic branch names
- `manager.md` - Phase 3: Coordinate full implementation (used by all 3 competing managers)
- `red-team.md` - Implementation specialist (reference for manager)
- `blue-team.md` - Quality assurance specialist (reference for manager)
- `judge.md` - Phase 4: Evaluate and score implementations
- `pr-creator.md` - Phase 6: Generate PR descriptions

Each agent has detailed instructions, best practices, and evaluation criteria.

[↑ Back to top](#table-of-contents)

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

[↑ Back to top](#table-of-contents)

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

[↑ Back to top](#table-of-contents)

---

## Configuration

### Quality Threshold

Edit `minidani.py`:

```python
self.QUALITY_THRESHOLD = 80  # Change to 70 or 90
```

**Recommended values:**
- `70` - Less strict (fewer retries)
- `80` - Balanced (default)
- `90` - Very strict (more retries, better quality)

### Timeouts

```python
# Manager execution timeout (default: 30 minutes per manager)
# Formula: 20 min base + 10 min per iteration
r = self.run_oc(..., timeout=1800)

# Judge timeout (default: 8 minutes)
r = self.run_oc(..., timeout=480)
```

[↑ Back to top](#table-of-contents)

---

## Troubleshooting

### OpenCode not found

```bash
# Check if OpenCode is installed
opencode --version

# If not in PATH, find it
which opencode

# Install from: https://github.com/unit-mesh/opencode
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

### ModuleNotFoundError: No module named 'rich'

```bash
pip install -r requirements.txt
```

[↑ Back to top](#table-of-contents)

---

## Advanced Usage

### Run Without TUI (headless)

Comment out the `with Live(...)` block and use plain print statements.

### Customize Manager Count

Currently hardcoded to 3 (A, B, C). To change:

1. Edit `self.state.managers = {...}` in `__init__`
2. Update all loops: `for m in ["a","b","c"]` → `for m in ["a","b","c","d"]`
3. Update Phase 2 setup and cleanup logic

[↑ Back to top](#table-of-contents)

---

## How Is This Different?

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **Single AI** | One agent implements | Fast | Limited quality |
| **Iterative refinement** | Agent + feedback loop | Improved quality | Time-consuming |
| **MiniDani** | 3 parallel + judge | Best quality, same time | Uses 3x compute |

**MiniDani's advantage:** Competitive pressure + parallel execution = better results in the same time as a single refined attempt.

[↑ Back to top](#table-of-contents)

---

## Contributing

Improvements welcome:

1. Fork the repo
2. Create branch: `git checkout -b feature/improvement`
3. Test with multiple tasks
4. Create PR with clear description

[↑ Back to top](#table-of-contents)

---

## License

MIT License - Use freely, improve, share.

[↑ Back to top](#table-of-contents)
