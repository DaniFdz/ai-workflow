---
name: minidani
description: Multi-agent competitive development orchestration patterns
---

# MiniDani Orchestration Skill

Patrones y best practices para desarrollo competitivo multi-agente.

## Core Concept

**Competición drive calidad.** 3 implementaciones en paralelo, la mejor gana.

## When to Use

✅ Feature compleja que requiere exploración  
✅ Calidad es crítica  
✅ Múltiples approaches posibles  
✅ Tienes tiempo y presupuesto para 3x implementaciones  

❌ Tarea trivial (overkill)  
❌ Deadline urgente  
❌ Presupuesto limitado  

## Pattern: Parallel Competition

```
User Prompt
    ↓
3 Managers (A, B, C) in parallel
    ↓
Judge (objective scoring)
    ↓
Winner selected
```

## Pattern: Quality Gate

```python
if max(scores) < 80:
    # All implementations subpar
    launch_round_2_with_feedback()
```

## Pattern: Clean PR

Antes de PR:
1. Remove losing worktrees
2. Clean internal files
3. Generate professional description
4. Only production code remains

## Scoring Guidelines

**Completeness (35 pts):**
- All requirements met: 35
- Most requirements: 30
- Basic functionality: 25
- Incomplete: <20

**Code Quality (30 pts):**
- Clean, maintainable: 30
- Good with minor issues: 25
- Needs improvement: 20
- Poor quality: <15

**Tests (25 pts):**
- >90% coverage, edge cases: 25
- >80% coverage: 20
- Basic tests: 15
- No tests: 0

**Best Practices (10 pts):**
- Type hints, docs, error handling: 10
- Mostly follows: 7
- Some gaps: 5
- Poor practices: <3

## Example Prompts

**Good:**
```
Implement OAuth2 authentication with:
- Google OAuth provider
- JWT token generation and validation
- Role-based access control
- Session management
- Tests with >80% coverage
```

**Too vague:**
```
Add auth
```

## When NOT to Use

Single implementation is better when:
- Simple, well-defined task
- Time is critical
- Token budget is tight
- You just need it done, not perfect
