# 📦 Instalación de MiniDani

Guía completa para instalar y configurar MiniDani.

---

## 📋 Requisitos Previos

### 1. Python 3.8+

```bash
python3 --version
# Python 3.8 o superior
```

### 2. Git

```bash
git --version
# git version 2.x
```

### 3. OpenCode CLI

```bash
ls ~/.opencode/bin/opencode
# Debe existir

# Si no existe, instalar OpenCode:
# https://opencode.ai/docs/installation
```

---

## 🚀 Instalación

### Opción 1: Clonar y Usar (Más Simple)

```bash
# 1. Clonar el repo
git clone https://github.com/tu-usuario/minidani.git ~/minidani

# 2. Instalar dependencias Python
cd ~/minidani
pip install -r requirements.txt

# 3. Hacer el script ejecutable desde cualquier lugar
chmod +x ~/minidani/minidani.py

# 4. (Opcional) Añadir alias a tu shell
echo 'alias minidani="python3 ~/minidani/minidani.py"' >> ~/.bashrc
source ~/.bashrc
```

**Uso:**
```bash
cd /path/to/tu-proyecto
minidani "Create a REST API for todos"
```

---

### Opción 2: Usar Stow para Linkear (Avanzado)

Stow permite crear symlinks organizados. Útil si quieres que `.opencode/` esté disponible globalmente.

#### Paso 1: Instalar Stow

```bash
# Ubuntu/Debian
sudo apt install stow

# macOS
brew install stow

# Arch
sudo pacman -S stow
```

#### Paso 2: Clonar MiniDani

```bash
git clone https://github.com/tu-usuario/minidani.git ~/minidani
cd ~/minidani
pip install -r requirements.txt
```

#### Paso 3: Linkear con Stow

**Opción A: Linkear a ~/.config/opencode**

```bash
cd ~/minidani

# Crear estructura si no existe
mkdir -p ~/.config/opencode

# Linkear .opencode/ a config global
stow -t ~/.config/opencode .opencode

# Verifica:
ls -la ~/.config/opencode/
# Deberías ver:
# agents/ -> /home/tu-usuario/minidani/.opencode/agents/
# skills/ -> /home/tu-usuario/minidani/.opencode/skills/
```

**Opción B: Linkear a un proyecto específico**

```bash
cd ~/minidani

# Linkear a tu proyecto
stow -t /path/to/tu-proyecto .

# Resultado:
# tu-proyecto/.opencode/ -> ~/minidani/.opencode/
# tu-proyecto/minidani.py -> ~/minidani/minidani.py
```

#### Paso 4: Verificar Links

```bash
# Ver qué se linkeó
stow -t ~/.config/opencode -n -v .opencode

# -n = dry-run (simula sin ejecutar)
# -v = verbose
```

#### Paso 5: Remover Links (si es necesario)

```bash
cd ~/minidani
stow -D -t ~/.config/opencode .opencode

# -D = delete (remueve symlinks)
```

---

### Opción 3: Symlink Manual (Sin Stow)

Si no quieres usar Stow:

```bash
# Linkear agents
ln -s ~/minidani/.opencode/agents ~/.config/opencode/minidani-agents

# Linkear skills  
ln -s ~/minidani/.opencode/skills/minidani ~/.config/opencode/skills/minidani

# Linkear script
ln -s ~/minidani/minidani.py ~/bin/minidani
chmod +x ~/bin/minidani
```

---

## 🧪 Verificar Instalación

### Test 1: Python y dependencias

```bash
python3 -c "import rich; print('✅ Rich instalado')"
```

### Test 2: OpenCode disponible

```bash
~/.opencode/bin/opencode -v
# Debería mostrar versión
```

### Test 3: MiniDani ejecutable

```bash
cd /tmp
mkdir test-minidani && cd test-minidani
git init
echo "# Test" > README.md
git add . && git commit -m "init"

# Ejecutar MiniDani
python3 ~/minidani/minidani.py "Create hello.py that prints hello world"

# Debería:
# - Crear 3 worktrees
# - Implementar en paralelo
# - Seleccionar ganador
# - Generar PR description
```

### Test 4: Cleanup

```bash
cd /tmp/test-minidani
git worktree list
# Debería mostrar solo el worktree ganador

# Limpiar
git worktree remove ../test-minidani_worktree_* --force
cd .. && rm -rf test-minidani
```

---

## 🔧 Configuración

### Cambiar Quality Threshold

Editar `minidani.py`:

```python
# Línea ~50
self.QUALITY_THRESHOLD = 80  # Cambiar a 70, 85, 90, etc.
```

**Valores recomendados:**
- `70` - Menos estricto (menos retries)
- `80` - Balanceado (default)
- `90` - Muy estricto (más retries, mejor calidad)

### Cambiar Timeout

```python
# En run_oc():
timeout=480  # 8 minutos por manager

# Para tareas muy complejas:
timeout=900  # 15 minutos
```

### Cambiar Número de Managers

**Por ahora:** Hardcoded a 3 (A, B, C)

**Para cambiar** (requiere editar múltiples lugares):
```python
# En __init__:
managers = {
    "a": ManagerState("a"),
    "b": ManagerState("b"),
    "c": ManagerState("c"),
    "d": ManagerState("d"),  # Añadir más
}

# En loops:
for mid in ["a", "b", "c", "d"]:  # Actualizar
    ...
```

---

## 🐳 Uso con Docker (Futuro)

Planeado para v2.0:

```bash
docker run -v $(pwd):/repo minidani/minidani \
  "Create a REST API for todos"
```

---

## 📊 Estructura Después de Instalación

```
~/
├── minidani/                    # Repo clonado
│   ├── minidani.py
│   ├── .opencode/
│   └── ...
│
├── .config/opencode/            # OpenCode global config
│   ├── agents/
│   │   └── minidani-* (symlinks) → ~/minidani/.opencode/agents/
│   └── skills/
│       └── minidani (symlink) → ~/minidani/.opencode/skills/minidani/
│
└── tu-proyecto/
    └── (aquí ejecutas minidani)
```

---

## ⚠️ Troubleshooting

### Stow da error "target exists"

```bash
# Ver qué existe
ls -la ~/.config/opencode/

# Si hay archivos existentes:
# Opción 1: Backup
mv ~/.config/opencode/agents ~/.config/opencode/agents.backup

# Opción 2: Merge manual
cp ~/minidani/.opencode/agents/* ~/.config/opencode/agents/
```

### "ModuleNotFoundError: No module named 'rich'"

```bash
pip install -r requirements.txt
# o
pip3 install --user rich>=13.7.0
```

### "OpenCode not found"

```bash
# Verificar instalación
which opencode

# Si no está en PATH:
export PATH="$HOME/.opencode/bin:$PATH"
echo 'export PATH="$HOME/.opencode/bin:$PATH"' >> ~/.bashrc
```

---

## 🔄 Actualizar MiniDani

```bash
cd ~/minidani
git pull origin main

# Si usas stow, los symlinks se actualizan automáticamente
# Si copiaste manualmente, vuelve a copiar
```

---

## 🗑️ Desinstalar

```bash
# Remover symlinks (si usaste stow)
cd ~/minidani
stow -D -t ~/.config/opencode .opencode

# Remover alias
# Editar ~/.bashrc y eliminar la línea del alias

# Remover repo
rm -rf ~/minidani

# Remover dependencias (opcional)
pip uninstall rich
```

---

**¿Dudas?** Abre un issue en GitHub o consulta `docs/QUICKSTART.md` 🦞
