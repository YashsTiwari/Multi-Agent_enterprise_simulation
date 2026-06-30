#!/bin/bash
# start.sh — run this on Mac instead of rag_server.py
# Auto-detects MAC IP, starts RAG server + dashboard

# Get Mac's current LAN IP
MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)

if [ -z "$MAC_IP" ]; then
  echo "ERROR: Could not detect IP. Check WiFi connection."
  exit 1
fi

echo "Mac IP: $MAC_IP"

# Kill anything on ports 8888 / 8080
lsof -ti:8888 | xargs kill -9 2>/dev/null
lsof -ti:8080 | xargs kill -9 2>/dev/null
sleep 1

# Team machine IPs (fixed — don't change)
TEAM_IPS="172.18.40.114"

# Start RAG server in background
cd "$(dirname "$0")/mac_control"
python3 rag_server.py &
RAG_PID=$!
sleep 2

# Start dashboard
cd "$(dirname "$0")"
python3 dashboard.py --rag "http://$MAC_IP:8888" --teams "$TEAM_IPS" &
DASH_PID=$!

echo ""
echo "=========================================="
echo "  RAG:        http://$MAC_IP:8888"
echo "  Scoreboard: http://$MAC_IP:8080/"
echo "  Control:    http://$MAC_IP:8080/control"
echo "=========================================="
echo "Press Ctrl+C to stop everything"

# Push MAC_IP to team machines so their config updates automatically
for IP in $(echo $TEAM_IPS | tr ',' ' '); do
  ssh -o ConnectTimeout=3 -o BatchMode=yes teaching@$IP \
    "sed -i 's|http://[0-9.]*:8888|http://$MAC_IP:8888|g' ~/nexaai/project/config.py" 2>/dev/null \
    && echo "Updated config on $IP" \
    || echo "Could not SSH to $IP — update config.py manually"
done

wait $RAG_PID $DASH_PID
