#!/bin/bash
# mac_setup.sh — Run this on the INSTRUCTOR'S MAC before the workshop
# Usage: bash mac_setup.sh
# Takes about 2 minutes.

set -e

echo ""
echo "=========================================="
echo "  NEXAAI — Instructor Mac Setup"
echo "=========================================="

# ── 1. Find Mac's IP on LAN ───────────────────────────────────────────
echo ""
echo "Step 1: Detecting Mac IP address on LAN..."
MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "NOT_FOUND")

if [ "$MAC_IP" = "NOT_FOUND" ]; then
    echo "  WARNING: Could not auto-detect IP. Run: ifconfig | grep 'inet '"
    echo "  Then update RAG_SERVER_URL in team machines' config.py"
else
    echo "  Mac IP: $MAC_IP"
    echo "  Team machines will connect to: http://$MAC_IP:8888"
fi

# ── 2. Install dependencies ───────────────────────────────────────────
echo ""
echo "Step 2: Installing Python dependencies..."
pip3 install flask requests --quiet
echo "  ✓ flask and requests installed"

# ── 3. Create directory structure ─────────────────────────────────────
echo ""
echo "Step 3: Creating Global RAG directory structure..."
mkdir -p global_rag/{scenario,market,releases,scores,regulation,news}
mkdir -p hurdles
mkdir -p submissions/{team_a,team_b,team_c,team_d}
echo "  ✓ Directories created"

# ── 4. Copy RAG files (assumes script is in mac_control/) ─────────────
echo ""
echo "Step 4: Copying initial RAG content..."

# These files should be in the same directory as this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

[ -f "$SCRIPT_DIR/global_rag/market/market_state.json" ] && cp "$SCRIPT_DIR/global_rag/market/market_state.json" global_rag/market/ && echo "  ✓ market_state.json"
[ -f "$SCRIPT_DIR/global_rag/scenario/active_scenario.md" ] && cp "$SCRIPT_DIR/global_rag/scenario/active_scenario.md" global_rag/scenario/ && echo "  ✓ active_scenario.md"
[ -f "$SCRIPT_DIR/global_rag/scores/scoreboard.md" ] && cp "$SCRIPT_DIR/global_rag/scores/scoreboard.md" global_rag/scores/ && echo "  ✓ scoreboard.md"
[ -f "$SCRIPT_DIR/global_rag/regulation/eu_ai_act_summary.md" ] && cp "$SCRIPT_DIR/global_rag/regulation/eu_ai_act_summary.md" global_rag/regulation/ && echo "  ✓ eu_ai_act_summary.md"

# Scenario history file (starts empty)
touch global_rag/scenario/scenario_history.md
echo "  ✓ scenario_history.md"

# ── 5. Copy hurdle files ───────────────────────────────────────────────
for h in H1 H2 H3; do
    [ -f "$SCRIPT_DIR/hurdles/${h}.md" ] && cp "$SCRIPT_DIR/hurdles/${h}.md" hurdles/ && echo "  ✓ hurdle ${h}.md"
done

# ── 6. Show IP for team config ────────────────────────────────────────
echo ""
echo "=========================================="
echo "  SETUP COMPLETE"
echo ""
echo "  IMPORTANT: Give this IP to all teams:"
echo "  → http://$MAC_IP:8888"
echo ""
echo "  Teams must update config.py:"
echo "  RAG_SERVER_URL = \"http://$MAC_IP:8888\""
echo ""
echo "  To start the RAG server:"
echo "  python3 rag_server.py"
echo ""
echo "  To check everything is working:"
echo "  python3 instructor_cli.py status"
echo "=========================================="
