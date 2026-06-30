#!/usr/bin/env python3
"""
Operation NexaAI — Instructor Control CLI
Run from the instructor's Mac to manage the simulation.

Usage:
    python3 instructor_cli.py status
    python3 instructor_cli.py inject H1
    python3 instructor_cli.py inject H2
    python3 instructor_cli.py inject H3
    python3 instructor_cli.py push market/market_state.json
    python3 instructor_cli.py scoreboard
    python3 instructor_cli.py releases
    python3 instructor_cli.py hash          ← check current RAG hash
"""

import sys, json, requests
from datetime import datetime

RAG_SERVER = "http://localhost:8888"  # Change if running server on different machine

def get(path):
    try:
        r = requests.get(f"{RAG_SERVER}/{path}", timeout=5)
        return r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
    except Exception as e:
        print(f"ERROR: Cannot reach RAG server at {RAG_SERVER}. Is rag_server.py running? ({e})")
        sys.exit(1)

def post(path, data=None):
    try:
        r = requests.post(f"{RAG_SERVER}/{path}", json=data, timeout=5)
        return r.json()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

def cmd_status():
    s = get("status")
    print(f"\n{'='*50}")
    print(f"  NEXAAI RAG SERVER STATUS")
    print(f"  Files in RAG:   {s['file_count']}")
    print(f"  Current hash:   {s['current_hash'][:16]}...")
    print(f"  History entries:{s['history_entries']}")
    print(f"  Server time:    {s['server_time']}")
    print(f"{'='*50}\n")

def cmd_hash():
    h = get("rag/hash")
    print(f"\n  Current RAG hash: {h['hash']}")
    print(f"  Files:            {h['file_count']}")
    print(f"  Timestamp:        {h['timestamp']}\n")

def cmd_inject(hurdle_id):
    valid = ["H1", "H2", "H3"]
    if hurdle_id not in valid:
        print(f"ERROR: Hurdle must be one of {valid}")
        sys.exit(1)
    print(f"\n  ► Injecting {hurdle_id}...")
    confirm = input(f"  Confirm: inject {hurdle_id} now? (y/n): ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return
    result = post(f"push/hurdle/{hurdle_id}")
    if result.get("ok"):
        print(f"\n  ✓ HURDLE {hurdle_id} INJECTED")
        print(f"  New hash: {result['hash'][:16]}...")
        print(f"  Market updates applied:")
        for k, v in result.get("market_updates", {}).items():
            print(f"    {k}: {v}")
        print(f"\n  ► Announce to students now!\n")
    else:
        print(f"  ✗ ERROR: {result}")

def cmd_push(filepath):
    """Push a specific file to the RAG server."""
    from pathlib import Path
    local = Path("global_rag") / filepath
    if not local.exists():
        print(f"ERROR: File not found: {local}")
        sys.exit(1)
    content = local.read_text()
    result = post("push", {"path": filepath, "content": content})
    if result.get("ok"):
        print(f"  ✓ Pushed: {filepath}")
        print(f"  New hash: {result['hash'][:16]}...")
    else:
        print(f"  ✗ ERROR: {result}")

def cmd_scoreboard():
    files = get("rag/all")
    sb = files.get("scores/scoreboard.md", "No scoreboard yet.")
    print("\n" + sb + "\n")

def cmd_releases():
    files = get("rag/all")
    bulletins = {k: v for k, v in files.items() if k.startswith("releases/")}
    if not bulletins:
        print("\n  No releases yet.\n")
        return
    for path, content in sorted(bulletins.items()):
        print(f"\n{'─'*50}")
        print(f"  {path}")
        print(f"{'─'*50}")
        print(content[:800])

def cmd_market():
    """Show current market state."""
    files = get("rag/all")
    ms = files.get("market/market_state.json", "{}")
    try:
        state = json.loads(ms)
        print(f"\n  CURRENT MARKET STATE")
        print(f"  {'─'*40}")
        for k, v in state.items():
            print(f"  {k}: {v}")
        print()
    except:
        print(ms)

def push_bulletin(team_id, scores, market_updates, release_number):
    """Push a release bulletin after evaluating a submission."""
    ts = datetime.utcnow().strftime("%H:%M")
    avg = sum(scores.values()) / len(scores)
    lines = [
        f"# MARKET BULLETIN — Release #{release_number}",
        f"# Time: {ts}  |  Company: {team_id.upper()}",
        f"",
        f"## Evaluation Scores",
    ]
    for dim, score in scores.items():
        lines.append(f"  {dim:<35} {score}/100")
    lines += [
        f"  {'WEIGHTED AVERAGE':<35} {avg:.1f}/100",
        f"",
        f"## Market Consequences (Effective Now)",
    ]
    for k, v in market_updates.items():
        lines.append(f"  {k}: {v}")
    content = "\n".join(lines)
    path = f"releases/release_bulletin_{release_number:03d}.md"
    result = post("push", {"path": path, "content": content})
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1].lower()
    if cmd == "status":
        cmd_status()
    elif cmd == "hash":
        cmd_hash()
    elif cmd == "inject":
        if len(sys.argv) < 3:
            print("Usage: python3 instructor_cli.py inject H1|H2|H3")
            sys.exit(1)
        cmd_inject(sys.argv[2].upper())
    elif cmd == "push":
        if len(sys.argv) < 3:
            print("Usage: python3 instructor_cli.py push <relative/path/in/rag>")
            sys.exit(1)
        cmd_push(sys.argv[2])
    elif cmd == "scoreboard":
        cmd_scoreboard()
    elif cmd == "releases":
        cmd_releases()
    elif cmd == "market":
        cmd_market()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
