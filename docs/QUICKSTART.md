# 🚀 MiniDani Quick Start

Ejecuta tu primera implementación competitiva en 5 minutos.

---

## Paso 1: Instalar

```bash
git clone https://github.com/tu-usuario/minidani.git
cd minidani
pip install -r requirements.txt
```

## Paso 2: Ir a Tu Proyecto

```bash
cd /path/to/tu-proyecto
```

## Paso 3: Ejecutar MiniDani

```bash
python3 /path/to/minidani/minidani.py "Create a simple calculator with add, subtract, multiply, divide"
```

**Verás:**

```
[17:41:39] [System] ℹ️ MiniDani Starting...
[17:41:45] [System] ✅ Branch: feature/calculator-api
[17:41:45] [System] ✅ Worktree A ready
[17:41:45] [System] ✅ Worktree B ready
[17:41:45] [System] ✅ Worktree C ready
[17:41:45] [Manager A] 🔄 Started
[17:41:45] [Manager B] 🔄 Started
[17:41:45] [Manager C] 🔄 Started
[17:42:35] [Manager B] ✅ Complete
[17:42:46] [Manager A] ✅ Complete
[17:43:02] [Manager C] ✅ Complete
[17:43:15] [System] ⚖️ Scores: A=93, B=95, C=89
[17:43:15] [System] 🏆 Winner: B
[17:43:27] [System] ✅ Complete in 107.4s

Winner: Manager B (95/100)
```

## Paso 4: Revisar Resultado

```bash
# Ver el worktree ganador
cd ../tu-proyecto_worktree_b

# Ver código
ls -la
cat app.py

# Ver PR description
cat PR_DESCRIPTION.md

# Ver tests
pytest test_app.py
```

## Paso 5: Crear PR (Manual)

```bash
# Desde el worktree ganador
git push origin feature/calculator-api-b

# Crear PR usando gh CLI
gh pr create --title "feat: calculator API" --body-file PR_DESCRIPTION.md
```

---

## Siguiente Nivel: Con TUI

Para ver progreso visual en tiempo real:

```bash
python3 /path/to/minidani/minidani_tui.py "Your task here"
```

Verás una interfaz con progress bars, estado de managers, y activity log.

---

## Tips

**1. Prompts claros = mejores resultados**
```
❌ "Add auth"
✅ "Implement OAuth2 authentication with Google provider, JWT tokens, and role-based permissions"
```

**2. Especifica success criteria**
```
Success criteria:
- All endpoints work
- Tests pass with >80% coverage
- Error handling for edge cases
```

**3. Usa minidani_retry.py para calidad máxima**
- Auto-retry si scores < 80
- Mejor para tareas complejas

---

**Tiempo estimado:**
- Tarea simple: ~1-2 min
- Tarea media: ~2-5 min
- Tarea compleja: ~5-10 min

¡Listo para competir! 🏆
