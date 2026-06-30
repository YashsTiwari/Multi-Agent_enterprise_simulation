#!/usr/bin/env python3
"""
Operation NexaAI — Global RAG Server (Fixed)
Run on instructor's Mac. All team machines read from here.

Usage:  python3 rag_server.py
"""

import os, json, hashlib, time
from pathlib import Path
from flask import Flask, jsonify, abort, request
from datetime import datetime

app = Flask(__name__)
RAG_DIR = Path(__file__).parent / "global_rag"

rag_history = []
MAX_HISTORY = 30


# ── FIX 1: Identical normalization to client ──────────────────────────
def _normalize(content: str) -> str:
    """Must match global_rag_client._normalize() exactly."""
    return content.replace('\r\n', '\n').replace('\r', '\n').strip()


def walk_rag_files() -> dict:
    """Returns {relative_path: content} for all .md and .json files.
    Explicitly excludes hidden files (e.g. .DS_Store on Mac)."""
    files = {}
    if not RAG_DIR.exists():
        return files
    for path in sorted(RAG_DIR.rglob("*")):
        # Skip hidden files and directories
        if any(part.startswith('.') for part in path.parts):
            continue
        if path.is_file() and path.suffix in (".md", ".json"):
            rel = str(path.relative_to(RAG_DIR))
            try:
                files[rel] = path.read_text(encoding="utf-8")
            except Exception:
                files[rel] = ""
    return files


def compute_hash(files: dict) -> str:
    """Must match global_rag_client._compute_hash() exactly."""
    parts = []
    for key in sorted(files.keys()):
        if key.endswith('.md') or key.endswith('.json'):
            parts.append(f"{key}||{_normalize(files[key])}")
    combined = "\n".join(parts)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def snapshot():
    files = walk_rag_files()
    h = compute_hash(files)
    return files, h


def record_rag_state(trigger="manual"):
    files, h = snapshot()
    entry = {
        "hash": h,
        "timestamp": datetime.utcnow().isoformat(),
        "trigger": trigger,
        "file_count": len(files)
    }
    rag_history.append(entry)
    if len(rag_history) > MAX_HISTORY:
        rag_history.pop(0)
    return h


# ── Endpoints ─────────────────────────────────────────────────────────

@app.route("/rag/all")
def get_all():
    files = walk_rag_files()
    return jsonify(files)


@app.route("/rag/hash")
def get_hash():
    files = walk_rag_files()
    h = compute_hash(files)
    return jsonify({
        "hash": h,
        "timestamp": datetime.utcnow().isoformat(),
        "file_count": len(files)
    })


@app.route("/rag/history")
def get_history():
    return jsonify(rag_history)


@app.route("/rag/<path:filepath>")
def get_file(filepath):
    full = RAG_DIR / filepath
    # Security: prevent directory traversal
    try:
        full.resolve().relative_to(RAG_DIR.resolve())
    except ValueError:
        abort(403)
    if full.exists() and full.is_file():
        return full.read_text(encoding="utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}
    abort(404)


@app.route("/status")
def status():
    files, h = snapshot()
    return jsonify({
        "status": "running",
        "rag_dir": str(RAG_DIR),
        "file_count": len(files),
        "current_hash": h,
        "hash_prefix": h[:16],
        "history_entries": len(rag_history),
        "server_time": datetime.utcnow().isoformat(),
        "last_trigger": rag_history[-1]["trigger"] if rag_history else "none",
    })


@app.route("/push", methods=["POST"])
def push_update():
    data = request.get_json()
    if not data or "path" not in data or "content" not in data:
        return jsonify({"error": "Need 'path' and 'content' fields"}), 400
    # Security: only allow .md and .json
    if not (data["path"].endswith(".md") or data["path"].endswith(".json")):
        return jsonify({"error": "Only .md and .json files allowed"}), 400
    target = RAG_DIR / data["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data["content"], encoding="utf-8")
    h = record_rag_state(trigger=f"push:{data['path']}")
    ts = datetime.utcnow().strftime('%H:%M:%S')
    print(f"[{ts}] PUSHED: {data['path']} → hash prefix {h[:12]}")
    return jsonify({"ok": True, "hash": h, "path": data["path"]})


@app.route("/push/hurdle/<hurdle_id>", methods=["POST"])
def push_hurdle(hurdle_id):
    valid = {"H1", "H2", "H3"}
    if hurdle_id not in valid:
        return jsonify({"error": f"Unknown hurdle. Must be one of {valid}"}), 400

    hurdle_path = Path(__file__).parent / "hurdles" / f"{hurdle_id}.md"
    if not hurdle_path.exists():
        return jsonify({"error": f"Hurdle file not found: {hurdle_path}"}), 404

    content = hurdle_path.read_text(encoding="utf-8")

    # Write active scenario
    (RAG_DIR / "scenario" / "active_scenario.md").write_text(content, encoding="utf-8")

    # Append to history
    history_path = RAG_DIR / "scenario" / "scenario_history.md"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(f"\n\n---\n# INJECTED: {hurdle_id} at {datetime.utcnow().isoformat()}\n\n{content}")

    # Apply market updates
    market_updates = HURDLE_MARKET_UPDATES.get(hurdle_id, {})
    if market_updates:
        market_file = RAG_DIR / "market" / "market_state.json"
        current = {}
        if market_file.exists():
            try:
                current = json.loads(market_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                current = {}
        current.update(market_updates)
        current["last_hurdle_injected"] = hurdle_id
        current["last_hurdle_time"] = datetime.utcnow().isoformat()
        market_file.write_text(json.dumps(current, indent=2), encoding="utf-8")

    h = record_rag_state(trigger=f"hurdle:{hurdle_id}")
    ts = datetime.utcnow().strftime('%H:%M:%S')
    print(f"[{ts}] ═══ HURDLE {hurdle_id} INJECTED ═══  hash prefix {h[:12]}")
    return jsonify({"ok": True, "hurdle": hurdle_id, "hash": h, "market_updates": market_updates})


HURDLE_MARKET_UPDATES = {
    "H1": {
        "hirebot_eu_status": "CHALLENGE_FILED",
        "hirebot_threat_score": 0.68,
        "active_eu_enterprise_waitlist": 300,
        "classification_challenge_active": True,
        "regulatory_scrutiny_level": "MEDIUM_HIGH",
    },
    "H2": {
        "deutsche_bank_status": "OFFER_ACTIVE",
        "deutsche_bank_contract_value": 10000000,
        "deutsche_bank_deadline_hours": 72,
        "contract_breach_penalty_base": 500000,
        "contract_breach_penalty_monthly_pct": 0.05,
    },
    "H3": {
        "emergency_directive_active": True,
        "directive_reference": "2026/447",
        "eu_explainability_standard_exists": False,
        "eu_training_data_available": False,
        "eu_training_data_eta": "Q4_2026",
        "deutsche_bank_contract_status": "UNCERTAIN",
        "regulatory_scrutiny_level": "CRITICAL",
        "personal_liability_active": True,
        "launch_30d_legally_possible": False,
        "launch_90d_legally_possible": "UNCERTAIN",
    }
}


if __name__ == "__main__":
    record_rag_state(trigger="server_start")
    files, h = snapshot()
    print(f"\n{'='*60}")
    print(f"  NEXAAI GLOBAL RAG SERVER")
    print(f"  RAG directory : {RAG_DIR}")
    print(f"  Serving on    : http://0.0.0.0:8888")
    print(f"  Files loaded  : {len(files)}")
    print(f"  Initial hash  : {h[:16]}...")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=8888, debug=False)
