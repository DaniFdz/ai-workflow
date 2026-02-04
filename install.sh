#!/usr/bin/env bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Get absolute path to this script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/.venv"
MINIDANI_SCRIPT="$SCRIPT_DIR/minidani.py"

echo ""
echo -e "${BLUE}${BOLD}🦞 MiniDani Installer${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Check Python version
echo -e "${BOLD}[1/6] Checking Python...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "  ${RED}❌ Python 3 not found${NC}"
    echo ""
    echo "Please install Python 3.8 or higher:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv"
    echo "  macOS: brew install python3"
    echo "  Arch: sudo pacman -S python"
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "  ${RED}❌ Python $PYTHON_VERSION found (minimum 3.8 required)${NC}"
    exit 1
fi

echo -e "  ${GREEN}✅ Python $PYTHON_VERSION (minimum 3.8 required)${NC}"
echo ""

# Step 2: Setup virtual environment
echo -e "${BOLD}[2/6] Setting up virtual environment...${NC}"

if [ -d "$VENV_PATH" ]; then
    echo -e "  ${YELLOW}⚠️  Existing venv found, reinstalling dependencies...${NC}"
    rm -rf "$VENV_PATH"
fi

python3 -m venv "$VENV_PATH"
echo -e "  ${GREEN}✅ Virtual environment created at: $VENV_PATH${NC}"

# Activate venv and install dependencies
source "$VENV_PATH/bin/activate"
pip install --upgrade pip > /dev/null 2>&1
pip install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1
deactivate

echo -e "  ${GREEN}✅ Dependencies installed${NC}"
echo ""

# Step 3: Check/install pi coding agent
echo -e "${BOLD}[3/6] Checking pi coding agent...${NC}"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "  ${RED}❌ Node.js not found${NC}"
    echo ""
    echo "Please install Node.js 20 or higher:"
    echo "  Ubuntu/Debian: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs"
    echo "  macOS: brew install node"
    echo "  Arch: sudo pacman -S nodejs npm"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo -e "  ${YELLOW}⚠️  Node.js version $(node --version) found (minimum v20 required)${NC}"
    echo "  Please upgrade Node.js to version 20 or higher"
    exit 1
fi
echo -e "  ${GREEN}✅ Node.js $(node --version) found${NC}"

# Check if pi coding agent is installed
if ! command -v pi &> /dev/null; then
    echo -e "  ${YELLOW}⚠️  Pi coding agent not found${NC}"
    echo -e "  ${BLUE}Installing pi coding agent...${NC}"
    npm install -g @mariozechner/pi-coding-agent
    if ! command -v pi &> /dev/null; then
        echo -e "  ${RED}❌ Failed to install pi coding agent${NC}"
        echo "  Please install manually: npm install -g @mariozechner/pi-coding-agent"
        exit 1
    fi
fi

PI_VERSION=$(pi --version 2>/dev/null | head -1 || echo "unknown")
echo -e "  ${GREEN}✅ Pi coding agent found: ${PI_VERSION}${NC}"
echo ""

# Step 4: Install agents (optional, for reference)
echo -e "${BOLD}[4/6] Installing agent prompts...${NC}"

AGENTS_SOURCE="$SCRIPT_DIR/agents"
AGENTS_DEST="$HOME/.config/minidani/agents"

if [ ! -d "$AGENTS_SOURCE" ]; then
    echo -e "  ${RED}❌ agents/ directory not found${NC}"
    exit 1
fi

# Create .config/minidani if it doesn't exist
mkdir -p "$HOME/.config/minidani"

# Backup existing agents if present
if [ -d "$AGENTS_DEST" ]; then
    BACKUP_PATH="${AGENTS_DEST}.backup.$(date +%s)"
    echo -e "  ${YELLOW}⚠️  Backing up existing agents to: $(basename $BACKUP_PATH)${NC}"
    mv "$AGENTS_DEST" "$BACKUP_PATH"
fi

# Copy agents
cp -r "$AGENTS_SOURCE" "$AGENTS_DEST"
AGENT_COUNT=$(ls -1 "$AGENTS_DEST" | grep -c '\.md$')

if [ $AGENT_COUNT -gt 0 ]; then
    echo -e "  ${GREEN}✅ Installed $AGENT_COUNT agent prompts to ~/.config/minidani/agents/${NC}"
    echo -e "  ${BLUE}📝 Available: manager, blue-team, red-team, judge, branch-namer, pr-creator${NC}"
else
    echo -e "  ${YELLOW}⚠️  No agent prompts found (optional)${NC}"
fi
echo ""

# Step 5: Find installation directory
echo -e "${BOLD}[5/6] Finding installation directory...${NC}"

POSSIBLE_BINS=(
    "$HOME/.local/bin"
    "$HOME/bin"
    "/usr/local/bin"
)

INSTALL_DIR=""
for bin_dir in "${POSSIBLE_BINS[@]}"; do
    if [[ ":$PATH:" == *":$bin_dir:"* ]]; then
        INSTALL_DIR="$bin_dir"
        echo -e "  ${GREEN}✅ Using: $INSTALL_DIR (already in PATH)${NC}"
        break
    fi
done

if [ -z "$INSTALL_DIR" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
    
    echo -e "  ${YELLOW}⚠️  No suitable directory found in PATH${NC}"
    echo -e "  ${BLUE}📁 Using: $INSTALL_DIR${NC}"
    echo ""
    echo -e "  ${BOLD}To use 'minidani' command, add this to your shell config:${NC}"
    echo ""
    
    if [ -n "$BASH_VERSION" ]; then
        echo -e "  ${BLUE}For bash:${NC}"
        echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
        echo "    source ~/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        echo -e "  ${BLUE}For zsh:${NC}"
        echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
        echo "    source ~/.zshrc"
    else
        echo -e "  ${BLUE}Add to your shell config:${NC}"
        echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
    echo ""
fi

# Step 6: Create wrapper script
echo -e "${BOLD}[6/6] Creating wrapper script...${NC}"

WRAPPER_PATH="$INSTALL_DIR/minidani"

cat > "$WRAPPER_PATH" << EOF
#!/usr/bin/env bash
# MiniDani wrapper - auto-generated by install.sh

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run minidani.py with all arguments
python3 "$MINIDANI_SCRIPT" "\$@"

# Exit with same code as minidani.py
exit \$?
EOF

chmod +x "$WRAPPER_PATH"
echo -e "  ${GREEN}✅ Executable created: $WRAPPER_PATH${NC}"
echo ""

# Final message
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}${BOLD}✅ Installation complete!${NC}"
echo ""
echo -e "${BOLD}Usage:${NC}"
echo "  cd /path/to/your/project"
echo ""
echo "  # Inline prompt"
echo "  minidani \"Add OAuth2 authentication\""
echo ""
echo "  # From file (recommended for complex prompts)"
echo "  minidani -f prompt.md"
echo ""
echo "  # From stdin"
echo "  cat prompt.md | minidani"
echo ""
echo -e "${BOLD}Configuration:${NC}"
echo "  Agent prompts: $SCRIPT_DIR/agents/"
echo "  Pi coding agent: $(which pi)"
echo "  Model: claude-sonnet-4-5 (configurable in minidani.py)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
