# 🦞 MiniDani

**Competitive parallel AI development system**

MiniDani runs 3 AI coding agents in parallel competing to implement your feature, then automatically selects and merges the best solution.

---

## Table of Contents

- [What is MiniDani?](#what-is-minidani)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [How It Works](#how-it-works)
- [Branch Prefix Configuration](#branch-prefix-configuration)
- [Branch Name Approval](#branch-name-approval)
- [Worktree Naming](#worktree-naming)
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
2. Each manager independently implements your feature using [OpenCode](https://opencode.ai)
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
1. **Branch name approval** - MiniDani proposes a branch name (e.g., `feature/oauth-auth`)
   - You have 20 seconds to approve (Y), reject (n), or provide custom name
   - If no response: auto-accepts proposed name
   - If rejected: prompts for manual entry
2. **Parallel execution** - 3 implementations start in isolated worktrees
3. **Live TUI** - Shows real-time progress (phases, managers, scores, activity log)
4. **Automatic selection** - Judge picks best implementation
5. **Ready to merge** - Winner branch ready for PR (30-40 min total)

[↑ Back to top](#table-of-contents)

---

## Installation

### Prerequisites

- **Python 3.8+**
- **OpenCode CLI** - Install with `npm install -g opencode-ai` (from [opencode.ai](https://opencode.ai))

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
[Phase 1] Generate branch name → oauth-auth (or feat/oauth-auth with prefix)
          ⏱️  20s approval window (auto-accept if no response)
          ✅ Y = Accept | ❌ n = Custom | any-name = Direct input
    ↓
[Phase 2] Create 3 git worktrees (isolated workspaces)
    ↓
[Phase 3] Run 3 Managers in parallel threads:
          Manager A: oauth-auth-r1-a (or feat/oauth-auth-r1-a with prefix)
          Manager B: oauth-auth-r1-b  
          Manager C: oauth-auth-r1-c
    ↓
[Phase 4] Judge evaluates all 3:
          A=87, B=95, C=82 → Winner: B
    ↓
[Phase 5] Cleanup: Delete worktrees A and C
    ↓
[Phase 6] Generate PR description from winner
    ↓
✅ Ready to merge oauth-auth-r1-b
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

## Branch Prefix Configuration

MiniDani allows you to customize the branch prefix used for generated branch names. **By default, no prefix is used** unless you configure one.

### Priority Order

Branch prefix is determined in this order:

1. **CLI argument** (`--branch-prefix`)
2. **Environment variable** (`$BRANCH_PREFIX`)
3. **No prefix** (empty string)

### Using Environment Variable

Set a global default prefix for all runs:

```bash
# In your ~/.bashrc or ~/.zshrc
export BRANCH_PREFIX="feat/"

# Now all MiniDani runs use feat/
minidani "Add authentication"
# → Generated: feat/auth or feat/add-auth
```

**Common prefixes:**
```bash
export BRANCH_PREFIX="feature/"   # Conventional commits style
export BRANCH_PREFIX="feat/"      # Short conventional
export BRANCH_PREFIX="bugfix/"    # For bug fixes
export BRANCH_PREFIX="fix/"       # Short bug fix
export BRANCH_PREFIX="chore/"     # For maintenance

# No need to set BRANCH_PREFIX="" - that's the default
# Just don't set the variable at all for no prefix
```

### Using CLI Argument

Override the prefix for a single run:

```bash
# Override env var or default
minidani --branch-prefix "fix/" "Fix login bug"
# → Generated: fix/login-bug

# Use a custom prefix
minidani --branch-prefix "experiment/" "Try new approach"
# → Generated: experiment/new-approach

# Explicitly no prefix (same as default behavior)
minidani --branch-prefix "" "Hotfix for production"
# → Generated: hotfix-production

# Or just don't set any prefix (default)
minidani "Hotfix for production"
# → Generated: hotfix-production (no prefix by default)
```

### Team Conventions

**Example 1: Jira ticket integration**
```bash
export BRANCH_PREFIX="PROJ-123/"
minidani "Add OAuth"
# → Generated: PROJ-123/oauth-auth
```

**Example 2: Developer name prefixes**
```bash
export BRANCH_PREFIX="john/"
minidani "Refactor database"
# → Generated: john/refactor-db
```

**Example 3: GitFlow style**
```bash
# Features
export BRANCH_PREFIX="feature/"
minidani "New API"  # → feature/new-api

# Hotfixes
minidani --branch-prefix "hotfix/" "Critical bug"  # → hotfix/critical-bug
```

### Custom Branch Names (No Prefix Required)

When you provide a **custom branch name** manually during approval, you don't need to include the configured prefix:

```bash
$ minidani "Add authentication"

🌿 Proposed branch name: feature/add-auth
   (using prefix: feature/)
Approve? [Y/n/custom name]: my-custom-branch↵

✅ Using custom branch: my-custom-branch
```

**The prefix is only used for AI-generated names**, not for your manual input. You have complete freedom when entering custom names.

[↑ Back to top](#table-of-contents)

---

## Branch Name Approval

After MiniDani generates a branch name, you have **20 seconds** to approve or customize it:

### Interactive Prompt

**Without prefix (default):**
```bash
==================================================
🌿 Proposed branch name: oauth-jwt-auth
   (no prefix configured)
==================================================
Approve? [Y/n/custom name]: 
(Auto-accept in 20s if no response)
```

**With prefix (e.g., `export BRANCH_PREFIX="feat/"`):**
```bash
==================================================
🌿 Proposed branch name: feat/oauth-jwt-auth
   (using prefix: feat/)
==================================================
Approve? [Y/n/custom name]: 
(Auto-accept in 20s if no response)
```

### Response Options

| Input | Action | Example |
|-------|--------|---------|
| **Y** or **yes** or **Enter** | Accept proposed name | `oauth-jwt-auth` (or `feat/oauth-jwt-auth` with prefix) |
| **n** or **no** | Prompt for custom entry | You provide: `my-auth` or `feat/my-auth` |
| **Any text** | Direct custom name | `my-custom-branch` (any format accepted) |
| *No response (20s)* | Auto-accept | `oauth-jwt-auth` |

### Examples

**Accept proposed name:**
```bash
Approve? [Y/n/custom name]: y
✅ Branch name approved
```

**Reject and provide custom:**
```bash
Approve? [Y/n/custom name]: n
Enter custom branch name: my-oauth-implementation
✅ Using custom branch: my-oauth-implementation
```

**Direct custom name (no prefix required):**
```bash
Approve? [Y/n/custom name]: awesome-auth-v2
✅ Using custom branch: awesome-auth-v2
```

**Custom name with your own prefix:**
```bash
Approve? [Y/n/custom name]: experimental/new-approach
✅ Using custom branch: experimental/new-approach
```

**Auto-accept (timeout):**
```bash
Approve? [Y/n/custom name]: 
⏱️  Timeout - auto-accepting branch name
```

**Why this matters:** Branch names become part of your git history and are visible in PRs. With configurable prefixes and manual override, you maintain consistency with your team's conventions while having full flexibility when needed.

[↑ Back to top](#table-of-contents)

---

## Worktree Naming

MiniDani creates isolated git worktrees for each competing manager. Understanding the naming scheme helps you locate and manage these directories.

### Naming Scheme

**Pattern:** `<repo_name>_<suffix>_r<round>_<id>`

- **repo_name**: Your repository's directory name
- **suffix**: Branch name without prefix (part after last `/`)
- **round**: Round number (1 or 2)
- **id**: Manager identifier (a, b, or c)

**Location:** `../<worktree_folder>/` (sibling to your repo)

### Examples

#### With Prefix (`export BRANCH_PREFIX="feat/"`)

| Branch Base | Suffix | Branch Git | Worktree Folder | Location |
|-------------|--------|------------|-----------------|----------|
| `feat/auth` | `auth` | `feat/auth-r1-a` | `myrepo_auth_r1_a` | `../myrepo_auth_r1_a/` |
| `feat/auth` | `auth` | `feat/auth-r1-b` | `myrepo_auth_r1_b` | `../myrepo_auth_r1_b/` |
| `feat/auth` | `auth` | `feat/auth-r1-c` | `myrepo_auth_r1_c` | `../myrepo_auth_r1_c/` |

#### Without Prefix (default)

| Branch Base | Suffix | Branch Git | Worktree Folder | Location |
|-------------|--------|------------|-----------------|----------|
| `auth` | `auth` | `auth-r1-a` | `myrepo_auth_r1_a` | `../myrepo_auth_r1_a/` |
| `auth` | `auth` | `auth-r1-b` | `myrepo_auth_r1_b` | `../myrepo_auth_r1_b/` |
| `auth` | `auth` | `auth-r1-c` | `myrepo_auth_r1_c` | `../myrepo_auth_r1_c/` |

#### Round 2 (Retry)

| Branch Base | Suffix | Branch Git | Worktree Folder | Location |
|-------------|--------|------------|-----------------|----------|
| `feat/auth` | `auth` | `feat/auth-r2-a` | `myrepo_auth_r2_a` | `../myrepo_auth_r2_a/` |
| `feat/auth` | `auth` | `feat/auth-r2-b` | `myrepo_auth_r2_b` | `../myrepo_auth_r2_b/` |
| `feat/auth` | `auth` | `feat/auth-r2-c` | `myrepo_auth_r2_c` | `../myrepo_auth_r2_c/` |

### Filesystem Structure

**Before cleanup** (all 3 managers running):
```
~/projects/
├── myrepo/                # Main repo
│   ├── .git/
│   └── src/
├── myrepo_auth_r1_a/      # Manager A worktree
│   └── src/
├── myrepo_auth_r1_b/      # Manager B worktree (winner)
│   └── src/
└── myrepo_auth_r1_c/      # Manager C worktree
    └── src/
```

**After cleanup** (winner selected: B):
```
~/projects/
├── myrepo/                # Main repo
│   ├── .git/
│   └── src/
└── myrepo_auth_r1_b/      # Winner's worktree - ready to merge
    └── src/
```

### Key Benefits

✅ **No slashes in folder names** - Avoids filesystem issues
✅ **Descriptive** - `myrepo_auth_r1_a` is clearer than `myrepo_worktree_r1_a`
✅ **Consistent** - Same folder name structure with or without prefix
✅ **Organized** - Easy to identify which worktree belongs to which feature

### Managing Worktrees Manually

If you need to manually manage worktrees:

```bash
# List all worktrees
git worktree list

# Remove a specific worktree
git worktree remove ../myrepo_auth_r1_a --force

# Remove associated branch
git branch -D auth-r1-a  # or feat/auth-r1-a with prefix
```

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

### Debug Mode

Enable detailed logging that prints after execution completes:

```bash
# Enable debug logs
minidani -d "Create API"
minidani --debug -f prompt.md

# Normal mode (no debug logs)
minidani "Create API"
```

**Debug output format:**
```
================================================================================
                                  DEBUG LOGS                                  
================================================================================
[2026-02-01 13:20:15.123] [Sys     ] [INFO   ] MiniDani Starting...
[2026-02-01 13:20:15.456] [Sys     ] [INFO   ] Gen branch
[2026-02-01 13:20:18.234] [Sys     ] [SUCCESS] Branch (approved): oauth-auth
[2026-02-01 13:20:18.567] [Sys     ] [INFO   ] Setup worktrees (Round 1)
[2026-02-01 13:20:19.123] [Sys     ] [SUCCESS] WT A R1
...
[2026-02-01 13:29:45.345] [Sys     ] [SUCCESS] Done 565.2s
================================================================================
Total debug entries: 21
================================================================================
```

**Log format:** `[timestamp] [manager] [level] message`
- **timestamp**: YYYY-MM-DD HH:MM:SS.mmm
- **manager**: Sys, MA, MB, MC (8 chars)
- **level**: INFO, SUCCESS, WORKING, JUDGE, WINNER, WARNING, ERROR (7 chars)

**When to use:**
- Debugging issues or failures
- Understanding execution timeline
- Analyzing performance bottlenecks
- Troubleshooting manager behavior

**Error logging:**
When managers, judge, or other agents fail, debug logs capture detailed error information:
```
[2026-02-01 13:25:45.123] [MA      ] [ERROR  ] Fail R1
[2026-02-01 13:25:45.124] [MA      ] [ERROR  ] Error details: Exit code 1
Stderr: OpenCode error: model timeout
Stdout: [partial output...]
```

This helps diagnose:
- Why a manager failed (timeout, model error, syntax error)
- Judge parsing errors or evaluation failures
- PR generation issues
- Branch name generation problems

**Benefits:**
- ✅ Doesn't clutter TUI during execution
- ✅ Complete log history with precise timestamps
- ✅ Easy to grep/filter for specific events
- ✅ Detailed error messages when things fail
- ✅ Helpful for bug reports with full context

### Practical Debugging Tips

**See all errors in real-time:**
```bash
# View all errors as they happen
minidani -d "task" 2>&1 | grep ERROR

# Save to file for later analysis
minidani -d "task" 2>&1 | tee debug.log
```

**Filter errors by manager:**
```bash
# See only Manager A errors
grep "\[MA\].*ERROR" debug.log

# See only Manager B errors
grep "\[MB\].*ERROR" debug.log

# See only Manager C errors
grep "\[MC\].*ERROR" debug.log
```

**Debug workflow:**
1. Manager fails → Check stderr in debug logs
2. Identify error cause (timeout, syntax, model issue)
3. Fix the root problem
4. Re-run with same prompt

**Common error patterns:**
```bash
# Model timeouts
grep "model timeout" debug.log

# Exit codes (non-zero = failure)
grep "Exit code [^0]" debug.log

# OpenCode specific errors
grep "OpenCode error" debug.log
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

# Install: npm install -g opencode-ai
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
