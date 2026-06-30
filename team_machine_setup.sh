#!/bin/bash
# team_machine_setup.sh — Run on each team machine (SSH in and run this)
# Usage: bash team_machine_setup.sh [team_id] [mac_ip]
# Example: bash team_machine_setup.sh team_a 192.168.1.42

set -e

TEAM_ID="${1:-team_a}"
MAC_IP="${2:-INSTRUCTOR_MAC_IP}"

echo ""
echo "=========================================="
echo "  NEXAAI — Team Machine Setup"
echo "  Team: $TEAM_ID"
echo "  RAG Server: $MAC_IP:8888"
echo "=========================================="

# ── 1. Activate venv and install packages ────────────────────────────
echo ""
echo "Step 1: Installing packages in agentic venv..."
source ~/agentic/bin/activate

pip install flask requests rich --quiet
echo "  ✓ flask, requests, rich installed"

# Check ollama Python client
pip show ollama > /dev/null 2>&1 || pip install ollama --quiet
echo "  ✓ ollama Python client present"

# ── 2. Pull Ollama models ─────────────────────────────────────────────
echo ""
echo "Step 2: Pulling Ollama models (this may take a few minutes)..."
echo "  Pulling llama3.2:3b..."
ollama pull llama3.2:3b
echo "  Pulling qwen2.5:7b..."
ollama pull qwen2.5:7b
echo "  ✓ Models ready"

# ── 3. Create project structure ───────────────────────────────────────
echo ""
echo "Step 3: Creating project structure..."
mkdir -p ~/nexaai/project/{agents,tools,knowledge/{finance,engineering,marketing,hr,legal,common},consensus,converter,state,submissions,logs}
echo "  ✓ Project structure created"

# ── 4. Copy starter code files ───────────────────────────────────────
echo ""
echo "Step 4: Installing starter code..."

STARTER_DIR="$(cd "$(dirname "$0")" && pwd)/team_machine"

# Copy all starter files
for f in config.py global_rag_client.py eval_interface.py main.py; do
    if [ -f "$STARTER_DIR/$f" ]; then
        cp "$STARTER_DIR/$f" ~/nexaai/project/
        echo "  ✓ $f"
    fi
done

# Copy agents directory
if [ -d "$STARTER_DIR/agents" ]; then
    cp -r "$STARTER_DIR/agents" ~/nexaai/project/
    echo "  ✓ agents/ directory"
fi

# ── 5. Configure team settings ───────────────────────────────────────
echo ""
echo "Step 5: Configuring team settings..."

# Update config.py with team-specific values
CONFIG_FILE=~/nexaai/project/config.py
sed -i "s/TEAM_ID = \"team_a\"/TEAM_ID = \"$TEAM_ID\"/" "$CONFIG_FILE"
sed -i "s|http://INSTRUCTOR_MAC_IP:8888|http://$MAC_IP:8888|" "$CONFIG_FILE"
echo "  ✓ config.py: TEAM_ID=$TEAM_ID, RAG_SERVER_URL=http://$MAC_IP:8888"

# ── 6. Lock eval_interface.py ────────────────────────────────────────
echo ""
echo "Step 6: Locking eval_interface.py..."
chmod 444 ~/nexaai/project/eval_interface.py
echo "  ✓ eval_interface.py is now read-only (chmod 444)"

# ── 7. Install code-server for browser-based collaboration ───────────
echo ""
echo "Step 7: Setting up code-server..."
if ! command -v code-server &> /dev/null; then
    echo "  Installing code-server..."
    curl -fsSL https://code-server.dev/install.sh | sh --version 4.22.1 2>/dev/null
fi

# Start code-server on port 8080 (no auth, so all team members can access)
pkill code-server 2>/dev/null || true
nohup code-server \
    --bind-addr 0.0.0.0:8080 \
    --auth none \
    ~/nexaai/project \
    > ~/nexaai/code-server.log 2>&1 &

echo "  ✓ code-server started"

# ── 8. Test RAG connection ────────────────────────────────────────────
echo ""
echo "Step 8: Testing Global RAG connection..."
sleep 2
if curl -s "http://$MAC_IP:8888/status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  ✓ RAG server OK: {d[\"file_count\"]} files')" 2>/dev/null; then
    echo ""
else
    echo "  ⚠ WARNING: Cannot reach RAG server at $MAC_IP:8888"
    echo "  Make sure instructor has started rag_server.py on their Mac"
    echo "  Or check if you are on the same WiFi network"
fi

# ── 9. Test Ollama ────────────────────────────────────────────────────
echo ""
echo "Step 9: Testing Ollama..."
if ollama list | grep -q "llama3.2:3b"; then
    echo "  ✓ llama3.2:3b available"
else
    echo "  ⚠ llama3.2:3b not found — run: ollama pull llama3.2:3b"
fi

# ── 10. Quick system test ─────────────────────────────────────────────
echo ""
echo "Step 10: Running system test..."
cd ~/nexaai/project
source ~/agentic/bin/activate
python3 -c "
from config import TEAM_ID, COMPANY_NAME, RAG_SERVER_URL
from global_rag_client import verify_rag_connection
print(f'  Team: {TEAM_ID} — {COMPANY_NAME}')
print(f'  RAG: {RAG_SERVER_URL}')
ok = verify_rag_connection()
" 2>/dev/null || echo "  (RAG test skipped — run manually after instructor starts server)"

# ── Done ──────────────────────────────────────────────────────────────
MACHINE_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=========================================="
echo "  SETUP COMPLETE — $TEAM_ID"
echo ""
echo "  Project folder: ~/nexaai/project/"
echo "  Code editor:    http://$MACHINE_IP:8080"
echo "  (Open this URL in any browser on this machine"
echo "   or from any laptop on the same WiFi)"
echo ""
echo "  To run the system:"
echo "  cd ~/nexaai/project"
echo "  source ~/agentic/bin/activate"
echo "  python main.py"
echo "=========================================="
