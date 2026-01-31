# MiniDani Agent System

This directory contains specialized agents used by MiniDani during the competitive development workflow.

## Agent Overview

### 1. branch-namer.md
**Phase:** 1 - Branch Generation  
**Purpose:** Analyze user request and generate semantic Git branch names  
**Input:** Task description  
**Output:** Branch name (e.g., `feature/oauth-jwt-auth`)

### 2. manager.md
**Phase:** 3 - Implementation  
**Purpose:** Coordinate complete feature implementation with quality standards  
**Input:** User task + optional feedback from previous round  
**Output:** Working code, tests, documentation  
**Used by:** All 3 competing managers (A, B, C)

### 3. red-team.md
**Reference Agent**  
**Purpose:** Implementation specialist guidelines (used by manager)  
**Focus:** Writing clean, correct, production-quality code  
**Contains:** Code patterns, best practices, anti-patterns, checklists

### 4. blue-team.md
**Reference Agent**  
**Purpose:** Quality assurance specialist guidelines (used by manager)  
**Focus:** Testing, validation, code review  
**Contains:** Test strategies, evaluation rubrics, bug reporting

### 5. judge.md
**Phase:** 4 - Evaluation  
**Purpose:** Objectively compare 3 implementations and select winner  
**Input:** Summaries from managers A, B, C  
**Output:** JSON with scores and winner selection  
**Criteria:** Completeness (35%), Quality (30%), Correctness (25%), Best Practices (10%)

### 6. pr-creator.md
**Phase:** 6 - PR Description  
**Purpose:** Generate professional pull request descriptions  
**Input:** Winning implementation details  
**Output:** Markdown PR description with summary, changes, testing, etc.

## How Agents Are Used

```python
# In minidani.py:

# Phase 1: Branch Naming
run_oc(prompt, agent="branch-namer")

# Phase 3: Implementation (x3 in parallel)
run_oc(user_task, worktree, agent="manager")

# Phase 4: Judging
run_oc(summaries, agent="judge")

# Phase 6: PR Creation
run_oc(winner_details, agent="pr-creator")
```

The agent's instructions are prepended to the user prompt, providing context and guidelines to OpenCode.

## Agent Design Principles

### 1. Specificity
Each agent has a single, well-defined responsibility.

### 2. Completeness
Agents include:
- Clear objectives
- Expected input/output formats
- Evaluation criteria
- Examples (good and bad)
- Best practices
- Common pitfalls

### 3. Consistency
All agents follow similar structure:
- Role definition
- Objective
- Guidelines/Criteria
- Examples
- Output format

### 4. Professional Quality
Agents are written in English with professional, technical tone suitable for production-level development.

## Customization

You can customize agents by:
1. Editing the `.md` files
2. Adjusting scoring criteria in `judge.md`
3. Changing code style guidelines in `red-team.md`
4. Modifying test strategies in `blue-team.md`

Changes take effect immediately (agents are loaded at runtime).

## Agent Interaction Flow

```
User Prompt
    ↓
[branch-namer] → Generate: feature/auth-jwt
    ↓
[manager A] ━┓
[manager B] ━╋→ Compete in parallel (each using manager.md)
[manager C] ━┛
    ↓
[judge] → Evaluate → Select winner (B: 95/100)
    ↓
[pr-creator] → Generate PR description
    ↓
Done
```

## Quality Assurance

The agent system ensures:
- ✅ Consistent code quality across all managers
- ✅ Objective evaluation criteria
- ✅ Professional documentation
- ✅ Best practices enforcement
- ✅ Clear expectations for all phases

---

**Note:** `red-team.md` and `blue-team.md` are reference agents (guidelines) rather than directly invoked agents. The `manager.md` agent coordinates implementation and quality assurance as a unified process.
