#!/bin/bash
# MASTER_SETUP.sh
# Run this on the INSTRUCTOR'S MAC to set everything up.
# It sets up the Mac AND SSHes into all 4 team machines to set them up.
#
# Prerequisites:
#   1. SSH keys set up for all team machines (ssh-copy-id user@machine-ip)
#   2. All machines on same WiFi/LAN
#   3. agentic venv exists on all team machines
#
# Usage:
#   bash MASTER_SETUP.sh
#
# Or set team machine IPs directly:
#   TEAM_A_IP=192.168.1.10 TEAM_B_IP=192.168.1.11 ... bash MASTER_SETUP.sh

set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  NEXAAI — MASTER SETUP              ║"
echo "║  Operation NexaAI Workshop           ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Configuration ─────────────────────────────────────────────────────
# CHANGE THESE to your actual machine IPs
TEAM_A_IP="${TEAM_A_IP:-192.168.1.10}"
TEAM_B_IP="${TEAM_B_IP:-192.168.1.11}"
TEAM_C_IP="${TEAM_C_IP:-192.168.1.12}"
TEAM_D_IP="${TEAM_D_IP:-192.168.1.13}"
TEAM_USER="${TEAM_USER:-student}"   # SSH username on team machines

MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")
if [ -z "$MAC_IP" ]; then
    echo "Could not detect Mac IP automatically."
    read -p "Enter your Mac's IP address (visible to team machines): " MAC_IP
fi

echo "Mac IP:    $MAC_IP"
echo "Team IPs:  A=$TEAM_A_IP  B=$TEAM_B_IP  C=$TEAM_C_IP  D=$TEAM_D_IP"
echo "SSH user:  $TEAM_USER"
echo ""
read -p "Proceed with setup? (y/n): " confirm
[ "$confirm" != "y" ] && echo "Cancelled." && exit 0

# ── Step 1: Mac Setup ─────────────────────────────────────────────────
echo ""
echo "══ Setting up instructor Mac..."
cd "$(dirname "$0")/mac_control"
pip3 install flask requests --quiet
mkdir -p global_rag/{scenario,market,releases,scores,regulation,news} hurdles
# (RAG initial files should already be present — see mac_control/global_rag/)
echo "  ✓ Mac setup complete"

# ── Step 2: Package starter code for transfer ─────────────────────────
echo ""
echo "══ Packaging starter code..."
TMPDIR=$(mktemp -d)
STARTER_ARCHIVE="$TMPDIR/nexaai_starter.tar.gz"
tar -czf "$STARTER_ARCHIVE" \
    -C "$(dirname "$0")" \
    team_machine/ \
    team_machine_setup.sh
echo "  ✓ Starter code packaged: $STARTER_ARCHIVE"

# ── Step 3: Setup each team machine ──────────────────────────────────
setup_machine() {
    local ip="$1"
    local team_id="$2"
    echo ""
    echo "══ Setting up $team_id ($ip)..."
    
    # Check connectivity
    if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$TEAM_USER@$ip" "echo ok" > /dev/null 2>&1; then
        echo "  ✗ Cannot SSH to $ip — skip. Set up manually later."
        return
    fi
    
    # Copy setup files
    scp -q "$STARTER_ARCHIVE" "$TEAM_USER@$ip:/tmp/nexaai_starter.tar.gz"
    
    # Run setup on remote machine
    ssh "$TEAM_USER@$ip" bash << REMOTE
        set -e
        cd /tmp
        tar -xzf nexaai_starter.tar.gz
        chmod +x team_machine_setup.sh
        bash team_machine_setup.sh "$team_id" "$MAC_IP"
REMOTE
    echo "  ✓ $team_id ($ip) setup complete"
}

setup_machine "$TEAM_A_IP" "team_a"
setup_machine "$TEAM_B_IP" "team_b"
setup_machine "$TEAM_C_IP" "team_c"
setup_machine "$TEAM_D_IP" "team_d"

# ── Step 4: Start Mac RAG server ─────────────────────────────────────
echo ""
echo "══ Starting Global RAG server on Mac..."
cd "$(dirname "$0")/mac_control"
pkill -f "rag_server.py" 2>/dev/null || true
nohup python3 rag_server.py > ~/nexaai_rag_server.log 2>&1 &
sleep 2
python3 instructor_cli.py status

# ── Step 5: Collect code-server URLs for students ─────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  SETUP COMPLETE — GIVE THESE TO STUDENTS ON MONDAY      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
printf "║  VeriHire AI  (team_a): http://%-26s║\n" "$TEAM_A_IP:8080"
printf "║  TalentLens   (team_b): http://%-26s║\n" "$TEAM_B_IP:8080"
printf "║  ClearPath AI (team_c): http://%-26s║\n" "$TEAM_C_IP:8080"
printf "║  NexaRecruit  (team_d): http://%-26s║\n" "$TEAM_D_IP:8080"
echo "║                                                          ║"
printf "║  Scoreboard: http://%-35s║\n" "$MAC_IP:8888/rag/scores/scoreboard.md"
echo "║                                                          ║"
echo "║  To inject hurdle H1:                                    ║"
echo "║  python3 instructor_cli.py inject H1                     ║"
echo "║                                                          ║"
echo "║  To check server status:                                 ║"
echo "║  python3 instructor_cli.py status                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Cleanup
rm -rf "$TMPDIR"
