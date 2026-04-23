#!/bin/bash
# CHOPPR — Mac Setup & Run Script
# Run this once to install everything, then again anytime to start the app.

set -e
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}  ██████╗██╗  ██╗ ██████╗ ██████╗ ██████╗ ██████╗ "
echo -e "  ██╔════╝██║  ██║██╔═══██╗██╔══██╗██╔══██╗██╔══██╗"
echo -e "  ██║     ███████║██║   ██║██████╔╝██████╔╝██████╔╝"
echo -e "  ██║     ██╔══██║██║   ██║██╔═══╝ ██╔═══╝ ██╔══██╗"
echo -e "  ╚██████╗██║  ██║╚██████╔╝██║     ██║     ██║  ██║"
echo -e "   ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝     ╚═╝  ╚═╝${NC}"
echo ""
echo -e "${CYAN}  YouTube → Shorts Engine${NC}"
echo ""

# ── 1. Homebrew ──
if ! command -v brew &>/dev/null; then
  echo -e "${YELLOW}Installing Homebrew...${NC}"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo -e "${GREEN}✓ Homebrew already installed${NC}"
fi

# ── 2. Python ──
if ! command -v python3 &>/dev/null; then
  echo -e "${YELLOW}Installing Python...${NC}"
  brew install python
else
  echo -e "${GREEN}✓ Python $(python3 --version | awk '{print $2}') already installed${NC}"
fi

# ── 3. FFmpeg ──
if ! command -v ffmpeg &>/dev/null; then
  echo -e "${YELLOW}Installing FFmpeg...${NC}"
  brew install ffmpeg
else
  echo -e "${GREEN}✓ FFmpeg already installed${NC}"
fi

# ── 4. yt-dlp ──
if ! command -v yt-dlp &>/dev/null; then
  echo -e "${YELLOW}Installing yt-dlp...${NC}"
  brew install yt-dlp
else
  echo -e "${GREEN}✓ yt-dlp already installed${NC}"
  # Always update yt-dlp (YouTube breaks it regularly)
  echo -e "${CYAN}  Updating yt-dlp...${NC}"
  yt-dlp -U 2>/dev/null || true
fi

# ── 5. Python venv + packages ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  echo -e "${YELLOW}Creating Python virtual environment...${NC}"
  python3 -m venv .venv
fi

source .venv/bin/activate
echo -e "${YELLOW}Installing Python packages...${NC}"
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Packages installed${NC}"

# ── 6. API Key ──
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo ""
  echo -e "${RED}⚠️  ANTHROPIC_API_KEY not set.${NC}"
  echo -e "   Get yours at: ${CYAN}https://console.anthropic.com/settings/keys${NC}"
  echo ""
  read -p "   Paste your Anthropic API key here: " api_key
  export ANTHROPIC_API_KEY="$api_key"
  echo ""
  # Optionally save to .env
  echo "ANTHROPIC_API_KEY=$api_key" > .env
  echo -e "${GREEN}✓ API key saved to .env${NC}"
else
  echo -e "${GREEN}✓ Anthropic API key found${NC}"
fi

# Load .env if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# ── 7. Launch ──
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  CHOPPR is starting on http://localhost:5055${NC}"
echo -e "${GREEN}  Opening in your browser...${NC}"
echo -e "${GREEN}  Press Ctrl+C to stop.${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

sleep 1
open "http://localhost:5055" 2>/dev/null || true

python3 app.py
