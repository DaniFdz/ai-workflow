# MiniDani Architecture

Diseño técnico del sistema multi-agente competitivo.

---

## 🏗️ Componentes

### 1. Orchestrator (Main Script)

**Responsabilidad:** Coordinar todo el flujo

**Fases:**
1. Branch Name Generator
2. Git Worktree Setup
3. Manager Execution (parallel)
4. Judging
5. Cleanup
6. PR Description Creation

**Implementación:** `minidani.py` (Python script)

### 2. Managers (x3)

**Responsabilidad:** Implementar la solución

**Proceso:**
- Reciben prompt original
- Usan OpenCode/Claude para implementar
- Commitan resultado en su worktree

**Paralelismo:** 3 threads Python ejecutándose simultáneamente

### 3. Judge

**Responsabilidad:** Evaluar objetivamente

**Scoring Rubric:**
- Completeness (35 pts): ¿Cumple todos los requisitos?
- Code Quality (30 pts): ¿Código limpio y mantenible?
- Correctness (25 pts): ¿Funciona correctamente?
- Best Practices (10 pts): ¿Sigue estándares?

**Total: 0-100 puntos**

### 4. PR Creator

**Responsabilidad:** Generar descripción profesional

**Inputs:**
- Prompt original
- Implementación ganadora
- Código final
- Scores de competición

**Output:** PR description en markdown

---

## 🔄 Flujo de Datos

```python
User Prompt (string)
    ↓
Branch Name (feature/...)
    ↓
3 Git Worktrees (paths)
    ↓
3 Manager Threads (parallel execution)
    ├─ Manager A → Implementation A
    ├─ Manager B → Implementation B
    └─ Manager C → Implementation C
    ↓
Judge (evaluates all 3)
    ↓
Scores { "a": 87, "b": 95, "c": 82 }
    ↓
Winner Selection (max score)
    ↓
Cleanup (remove losers)
    ↓
PR Description (from winner)
    ↓
Final Output
```

---

## 🧵 Threading Model

**Main Thread:**
- UI rendering (TUI con Rich)
- State management
- Phase coordination

**Worker Threads (3):**
- Manager A execution
- Manager B execution
- Manager C execution

**Thread Safety:**
- `threading.Lock` protege `state.activity_log`
- Cada manager tiene su propio worktree (no conflicts)

---

## 💾 State Management

### SystemState

```python
@dataclass
class SystemState:
    prompt: str
    repo_path: Path
    branch_base: str
    current_phase: int
    current_round: int
    managers: Dict[str, ManagerState]
    activity_log: List[tuple]
    winner: Optional[str]
```

### ManagerState

```python
@dataclass
class ManagerState:
    id: str
    status: str  # pending, running, complete, failed
    iteration: int
    worktree: Path
    branch: str
    score: Optional[int]
    summary: str
    round: int  # For retry logic
```

---

## 🔄 Retry Logic

### Quality Threshold

```python
QUALITY_THRESHOLD = 80

if max(scores) < QUALITY_THRESHOLD:
    start_round_2()
```

### Round 2 Improvements

**Feedback to managers:**
```
Previous round had low quality. Focus on:
- Complete implementation
- Comprehensive tests
- Good documentation
- Error handling
```

**Judge prompt updated:**
```
Be strict but fair.
Simple working solution: 80-90 pts
Comprehensive with tests: 90-100 pts
```

---

## 🎨 TUI Architecture

### Layout Structure

```
┌─────────────────────────────────────┐
│ Header (branch, time, round)        │
├──────────────┬──────────────────────┤
│ Phase        │ Managers             │
│ Progress     │ (A, B, C status)     │
│              ├──────────────────────┤
│              │ Activity Log         │
├──────────────┴──────────────────────┤
│ Footer (winner or status)           │
└─────────────────────────────────────┘
```

### Update Frequency

- **4 FPS** (4 updates per second)
- Thread-safe state updates
- Live rendering with Rich

---

## 📊 Performance Characteristics

**Tiempo esperado:**

| Tarea | Round 1 | Round 2 (si aplica) | Total |
|-------|---------|---------------------|-------|
| Simple | 60-90s | 60-90s | 1-3 min |
| Media | 90-180s | 90-180s | 2-6 min |
| Compleja | 180-480s | 180-480s | 5-15 min |

**Token usage:**
- ~3x una implementación normal (3 managers en paralelo)
- Round 2 duplica el costo

**Beneficio:**
- Múltiples approaches explorados
- Mejor calidad final
- Competición drive innovation

---

## 🐛 Error Handling

### Manager Fails

Si un manager falla:
- Status = "failed"
- Judge evalúa solo los que completaron
- Mínimo 1 debe completar para continuar

### Judge Fails

Fallback automático:
- Selecciona primer manager que completó
- Score = 85 (default)

### OpenCode Timeout

```python
timeout=480  # 8 min max por manager
```

Si timeout → manager marked as failed

---

## 🔮 Futuras Mejoras

### Potenciales

1. **Red/Blue Cycles dentro de managers**
   - Implementer → Reviewer → Rework loop
   - Requiere más orchestration

2. **Scoring más granular**
   - Test coverage actual
   - Lint/type check results
   - Performance benchmarks

3. **Adaptive retry**
   - Si A=95, B=50, C=45 → solo retry B y C

4. **Human-in-the-loop**
   - Pause antes de judging
   - Manual review option

5. **Budget limits**
   - Max tokens per manager
   - Early termination si uno domina

---

## 📚 Referencias

- OpenCode: https://opencode.ai
- Rich: https://rich.readthedocs.io
- Git Worktrees: `man git-worktree`

---

**Version:** 1.0  
**Last updated:** 2026-01-31
