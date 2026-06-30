#!/usr/bin/env python3
"""
Operation NexaAI — Instructor Dashboard
========================================
Run:
    python3 dashboard.py --rag http://172.16.8.221:8888 --teams 172.18.40.114

Args:
    --rag    URL of the Global RAG server   (default: http://localhost:8888)
    --teams  Comma-separated team machine IPs  (default: 172.18.40.114)
    --user   SSH username on team machines  (default: teaching)
    --port   Dashboard port                 (default: 8080)

URLs:
    http://localhost:8080/          → Public scoreboard (show on projector)
    http://localhost:8080/control   → Instructor control panel
"""

import argparse, json, os, re, threading, time, subprocess, hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import requests
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

# ── CLI args ─────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--rag",   default="http://localhost:8888", help="Global RAG server URL")
parser.add_argument("--teams", default="172.18.40.114",         help="Comma-separated team machine IPs")
parser.add_argument("--user",  default="teaching",              help="SSH user on team machines")
parser.add_argument("--port",  default=8080, type=int,          help="Dashboard port")
args = parser.parse_args()

RAG_URL     = args.rag
TEAM_IPS    = [ip.strip() for ip in args.teams.split(",")]
SSH_USER    = args.user
TEAM_IDS    = ["team_a", "team_b", "team_c", "team_d"]
TEAM_NAMES  = {
    "team_a": "VeriHire AI",
    "team_b": "TalentLens",
    "team_c": "ClearPath AI",
    "team_d": "NexaRecruit",
}
TEAM_COLORS = {
    "team_a": "#1F3864",
    "team_b": "#1A5C2E",
    "team_c": "#3B1F6E",
    "team_d": "#0C5460",
}
TEAM_IP_MAP = {TEAM_IDS[i]: TEAM_IPS[i] if i < len(TEAM_IPS) else None for i in range(4)}

SUBMISSIONS_DIR = Path(__file__).parent / "collected_submissions"
SUBMISSIONS_DIR.mkdir(exist_ok=True)

# ── In-memory state ──────────────────────────────────────────────────
state = {
    "scores": {tid: {"overall":0,"dimensions":{
        "incommensurability":0,"contradiction":0,"stability":0,"calibration":0,
        "info_gap":0,"hard_floor":0,"cross_dept":0,"traceability":0
    },"penalty":0,"submission_count":0,"last_submission":None,"market_share":1.0} for tid in TEAM_IDS},
    "market": {},
    "scenario": "H0",
    "last_updated": None,
    "submissions": [],
    "log": [],
}
state_lock = threading.Lock()

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    with state_lock:
        state["log"].insert(0, entry)
        state["log"] = state["log"][:50]
    print(entry)

# ── SCORER ───────────────────────────────────────────────────────────

PENALTY_RATES = {1:0, 2:0.05, 3:0.12, 4:0.22}

def get_penalty(sub_number: int) -> float:
    return PENALTY_RATES.get(sub_number, 0.35)

def score_submission(sub: dict) -> dict:
    """
    Auto-scores a submission across 8 dimensions.
    Returns {dimension: score} and overall weighted score.
    """
    scores = {}
    dept_outputs = sub.get("department_outputs", {})
    ceo = sub.get("ceo_decision", {})

    # ── 1. Incommensurability Resolution (18) ────────────────────────
    s = 0
    conv = ceo.get("converter_output", {})
    if conv:
        s += 4
        depts_converted = sum(1 for d in ["finance","engineering","marketing","hr","legal"] if f"{d}_converted" in conv)
        s += min(8, depts_converted * 2)  # 2pts per dept, max 8
        unit = conv.get("conversion_unit","")
        if unit and unit.lower() not in ("placeholder","todo","","none","placeholder — choose your unit"):
            s += 3
        if conv.get("uncertainty_ranges") and len(conv.get("uncertainty_ranges",{})) >= 4:
            s += 3
    scores["incommensurability"] = min(18, s)

    # ── 2. Contradiction Detection (18) ──────────────────────────────
    s = 0
    checked = ceo.get("commitments_checked", [])
    if checked and checked != ["PLACEHOLDER: list prior commitments checked"]:
        s += 8
    contradictions = ceo.get("contradictions_found", [])
    if isinstance(contradictions, list):
        s += 4
    if ceo.get("contradiction_resolution") and len(ceo.get("contradiction_resolution","")) > 20:
        s += 6
    scores["contradiction"] = min(18, s)

    # ── 3. Consensus Stability (18) ──────────────────────────────────
    s = 0
    if ceo.get("consensus_stable") is True:
        s += 9
    if ceo.get("consistency_hash") and len(ceo.get("consistency_hash","")) > 10:
        s += 5
    algo = ceo.get("consensus_algorithm","")
    if algo and algo.lower() not in ("placeholder — implement consensusengine","todo",""):
        s += 4
    scores["stability"] = min(18, s)

    # ── 4. Calibration Tracking (12) ─────────────────────────────────
    s = 0
    weights = ceo.get("calibration_weights_used", {})
    if weights and len(weights) == 5:
        vals = list(weights.values())
        if max(vals) - min(vals) > 0.01:  # not all equal
            s += 7
            if abs(sum(vals) - 1.0) < 0.02:
                s += 5
        else:
            s += 3  # has weights but all equal (default)
    scores["calibration"] = min(12, s)

    # ── 5. Information Gap Detection (12) ────────────────────────────
    s = 0
    gaps = ceo.get("information_gaps_flagged", [])
    if gaps and gaps != ["PLACEHOLDER: implement information gap detection"]:
        s += 5
    gap_conf = ceo.get("gap_adjusted_confidence", 1.0)
    dec_conf  = ceo.get("decision_confidence", 1.0)
    if isinstance(gap_conf, (int,float)) and isinstance(dec_conf, (int,float)):
        if gap_conf < dec_conf:
            s += 4
    # Check dept completeness
    incomplete_depts = sum(1 for d in dept_outputs.values()
                          if d.get("information_completeness",1.0) < 0.9)
    if incomplete_depts >= 2:
        s += 3
    scores["info_gap"] = min(12, s)

    # ── 6. Hard Constraint Enforcement (10) ──────────────────────────
    s = 0
    floors_active = ceo.get("hard_floors_active", [])
    # Check that hard_floor_breached field exists in all depts
    depts_with_floor = sum(1 for d in dept_outputs.values() if "hard_floor_breached" in d)
    s += min(5, depts_with_floor)  # 1pt per dept
    if ceo.get("vetoes_received") is not None:
        s += 3
    if floors_active is not None:
        s += 2
    scores["hard_floor"] = min(10, s)

    # ── 7. Cross-Department Consistency (7) ──────────────────────────
    s = 0
    xd = ceo.get("cross_dept_checks", {})
    if xd:
        s += 2
        if xd.get("engineering_used_hr_capacity") is True:
            s += 2
        if xd.get("finance_used_hr_hiring_cost") is True:
            s += 2
        conflicts = xd.get("consistency_conflicts", [])
        if isinstance(conflicts, list) and conflicts and \
           conflicts != ["PLACEHOLDER: placeholder shows data flow — real agents must actually chain outputs"]:
            s += 1
    scores["cross_dept"] = min(7, s)

    # ── 8. Decision Traceability (5) ─────────────────────────────────
    s = 0
    reasoning = ceo.get("reasoning","")
    if len(reasoning) >= 300:
        s += 2
    # Check for tool citations
    tool_pattern = re.compile(r'\w+\.\w+\(|\w+_tool|\w+\.calculate_|\w+\.model_|\w+\.estimate_', re.I)
    if tool_pattern.search(reasoning):
        s += 2
    all_tools = ceo.get("tools_called",[])
    if all_tools and all_tools != ["placeholder_ceo_tool"]:
        s += 1
    scores["traceability"] = min(5, s)

    # ── Weighted total ─────────────────────────────────────────────────
    weights_map = {
        "incommensurability":0.18,"contradiction":0.18,"stability":0.18,
        "calibration":0.12,"info_gap":0.12,"hard_floor":0.10,
        "cross_dept":0.07,"traceability":0.05
    }
    max_scores = {
        "incommensurability":18,"contradiction":18,"stability":18,
        "calibration":12,"info_gap":12,"hard_floor":10,
        "cross_dept":7,"traceability":5
    }
    total_pct = sum(
        (scores[k] / max_scores[k]) * weights_map[k]
        for k in scores
    ) * 100

    return {"dimensions": scores, "total_pct": round(total_pct, 1), "max_scores": max_scores}


# ── SUBMISSION COLLECTOR ──────────────────────────────────────────────

def collect_from_machine(team_id: str, ip: str) -> list:
    """SSH into team machine and rsync new submissions."""
    if not ip:
        return []
    remote_path = f"{SSH_USER}@{ip}:/home/{SSH_USER}/nexaai/project/submissions/"
    local_path  = SUBMISSIONS_DIR / team_id
    local_path.mkdir(exist_ok=True)

    cmd = ["rsync", "-av", "--update", "--ignore-existing",
           "-e", "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes",
           remote_path, str(local_path) + "/"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            new_files = [f for f in local_path.glob("submission_*.json")]
            log(f"Collected {len(new_files)} submissions from {team_id} ({ip})")
            return new_files
        else:
            log(f"SSH collect {team_id} failed: {result.stderr[:100]}")
            return []
    except Exception as e:
        log(f"Collect error {team_id}: {e}")
        return []

def collect_all():
    """Collect submissions from all team machines."""
    for team_id, ip in TEAM_IP_MAP.items():
        if ip:
            collect_from_machine(team_id, ip)

def process_submissions():
    """Read all local submissions and update scores."""
    all_subs = []
    for team_id in TEAM_IDS:
        team_dir = SUBMISSIONS_DIR / team_id
        if not team_dir.exists():
            continue
        files = sorted(team_dir.glob("submission_*.json"))
        team_subs = []
        for f in files:
            try:
                sub = json.loads(f.read_text())
                sub["_file"] = f.name
                sub["_team_id"] = team_id
                team_subs.append(sub)
            except Exception:
                pass

        if not team_subs:
            continue

        # Score the latest submission
        latest = team_subs[-1]
        sub_number = latest.get("submission_number", len(team_subs))
        penalty    = get_penalty(sub_number)
        result     = score_submission(latest)
        final_score = result["total_pct"] * (1 - penalty)

        with state_lock:
            state["scores"][team_id].update({
                "overall":         round(final_score, 1),
                "dimensions":      result["dimensions"],
                "max_scores":      result["max_scores"],
                "penalty":         penalty,
                "submission_count": sub_number,
                "last_submission": latest.get("submission_timestamp",""),
                "scenario":        latest.get("active_scenario_id","H0"),
                "rag_hash":        latest.get("rag_snapshot_hash","")[:12] + "...",
            })

        all_subs.extend(team_subs)

    with state_lock:
        state["submissions"] = sorted(all_subs,
            key=lambda s: s.get("submission_timestamp",""), reverse=True)[:50]

def refresh_from_rag():
    """Pull market state and scenario from Global RAG."""
    try:
        files = requests.get(f"{RAG_URL}/rag/all", timeout=5).json()
        market_json = files.get("market/market_state.json", "{}")
        market = json.loads(market_json)
        scenario_text = files.get("scenario/active_scenario.md","")
        scenario_id = "H0"
        for line in scenario_text.split("\n"):
            if line.startswith("# ACTIVE SCENARIO"):
                parts = line.split("—")
                if len(parts) >= 2:
                    scenario_id = parts[1].strip().split()[0]
                break
        with state_lock:
            state["market"] = market
            state["scenario"] = scenario_id
            state["last_updated"] = datetime.now().strftime("%H:%M:%S")
            # Update market share per team
            for tid in TEAM_IDS:
                state["scores"][tid]["market_share"] = market.get("eu_available_market_share", 1.0)
    except Exception as e:
        log(f"RAG refresh error: {e}")

def push_scoreboard_to_rag():
    """Build scoreboard.md and push to RAG."""
    with state_lock:
        scores = dict(state["scores"])
        scenario = state["scenario"]
        market = dict(state.get("market",{}))

    lines = [
        f"# OPERATION NEXAAI — LIVE SCOREBOARD",
        f"# Last updated: {datetime.now().strftime('%H:%M:%S')}",
        f"# Active Hurdle: {scenario}",
        "",
        f"{'Company':<20} {'Incom':>6} {'Contr':>6} {'Stab':>6} {'Calib':>6} {'IGap':>6} {'HFlr':>6} {'XDept':>6} {'Trace':>6} {'TOTAL':>7} {'Sub#':>5}",
        "-" * 90,
    ]
    for tid in TEAM_IDS:
        s = scores[tid]
        d = s.get("dimensions",{})
        penalty_str = f"(-{int(s['penalty']*100)}%)" if s['penalty'] > 0 else ""
        lines.append(
            f"{TEAM_NAMES[tid]:<20} "
            f"{d.get('incommensurability',0):>5}/18 "
            f"{d.get('contradiction',0):>5}/18 "
            f"{d.get('stability',0):>5}/18 "
            f"{d.get('calibration',0):>5}/12 "
            f"{d.get('info_gap',0):>5}/12 "
            f"{d.get('hard_floor',0):>5}/10 "
            f"{d.get('cross_dept',0):>5}/7  "
            f"{d.get('traceability',0):>4}/5  "
            f"{s['overall']:>6.1f}% "
            f"{s['submission_count']:>3} {penalty_str}"
        )

    lines += ["", "## Market State"]
    for k,v in market.items():
        lines.append(f"  {k}: {v}")

    content = "\n".join(lines)
    try:
        resp = requests.post(f"{RAG_URL}/push",
            json={"path":"scores/scoreboard.md","content":content}, timeout=5)
        log("Scoreboard pushed to RAG" if resp.json().get("ok") else "Scoreboard push failed")
    except Exception as e:
        log(f"Push scoreboard error: {e}")

def inject_hurdle(hurdle_id: str):
    """Inject a hurdle via RAG server API."""
    try:
        resp = requests.post(f"{RAG_URL}/push/hurdle/{hurdle_id}", timeout=10)
        data = resp.json()
        if data.get("ok"):
            log(f"✓ HURDLE {hurdle_id} INJECTED — new hash: {data.get('hash','')[:12]}...")
            return True, f"Hurdle {hurdle_id} injected. New RAG hash: {data.get('hash','')[:16]}"
        else:
            return False, str(data)
    except Exception as e:
        return False, str(e)

# ── BACKGROUND THREAD ─────────────────────────────────────────────────

def background_refresh():
    while True:
        try:
            refresh_from_rag()
            process_submissions()
        except Exception as e:
            log(f"BG error: {e}")
        time.sleep(8)

threading.Thread(target=background_refresh, daemon=True).start()

# ── FLASK APP ─────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

# ── SCOREBOARD PAGE ───────────────────────────────────────────────────

SCOREBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NexaAI — Live Scoreboard</title>
<style>
  :root{--bg:#0A0E1A;--card:#111827;--border:#1F2937;--text:#F9FAFB;--muted:#9CA3AF;--accent:#3B82F6}
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;padding:16px}
  header{text-align:center;margin-bottom:20px}
  header h1{font-size:2.4rem;font-weight:800;letter-spacing:2px;color:#fff}
  header .sub{color:var(--muted);font-size:1rem;margin-top:4px}
  .badge{display:inline-block;padding:3px 14px;border-radius:99px;font-size:.85rem;font-weight:700;margin-left:8px}
  .badge-h0{background:#374151;color:#D1D5DB}
  .badge-h1{background:#78350F;color:#FDE68A}
  .badge-h2{background:#064E3B;color:#6EE7B7}
  .badge-h3{background:#7F1D1D;color:#FCA5A5}
  .meta{display:flex;justify-content:center;gap:32px;margin-bottom:24px;font-size:.85rem;color:var(--muted)}
  .meta span b{color:#fff}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:1400px;margin:0 auto}
  .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;position:relative;overflow:hidden}
  .card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px}
  .card[data-team="team_a"]::before{background:#1F3864}
  .card[data-team="team_b"]::before{background:#1A5C2E}
  .card[data-team="team_c"]::before{background:#3B1F6E}
  .card[data-team="team_d"]::before{background:#0C5460}
  .card-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px}
  .company-name{font-size:1.5rem;font-weight:700;color:#fff}
  .overall-score{font-size:2.4rem;font-weight:800;line-height:1}
  .score-label{font-size:.72rem;color:var(--muted);text-align:right}
  .penalty-badge{font-size:.72rem;background:#7F1D1D;color:#FCA5A5;padding:2px 8px;border-radius:99px;margin-top:4px}
  .dims{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:12px}
  .dim{background:#1F2937;border-radius:6px;padding:7px 8px}
  .dim-label{font-size:.62rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
  .dim-bar-wrap{margin-top:4px;height:5px;background:#374151;border-radius:3px;overflow:hidden}
  .dim-bar{height:100%;border-radius:3px;transition:width .5s ease}
  .dim-val{font-size:.78rem;font-weight:600;margin-top:3px;color:#fff}
  .market-bar{margin-top:12px;background:#1F2937;border-radius:6px;padding:8px 10px}
  .market-label{font-size:.68rem;color:var(--muted)}
  .market-share-bar{margin-top:4px;height:8px;background:#374151;border-radius:4px;overflow:hidden}
  .market-share-fill{height:100%;background:linear-gradient(90deg,#3B82F6,#06B6D4);border-radius:4px;transition:width .8s ease}
  .sub-info{margin-top:8px;font-size:.72rem;color:var(--muted);display:flex;gap:12px}
  .ticker{max-width:1400px;margin:16px auto 0;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px 16px;display:flex;gap:24px;flex-wrap:wrap;font-size:.82rem}
  .tick-item{color:var(--muted)}.tick-item b{color:#fff}
  .live-dot{width:8px;height:8px;background:#10B981;border-radius:50%;display:inline-block;animation:pulse 2s infinite;margin-right:6px}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  .dim-bar-incomm{background:#F59E0B}
  .dim-bar-contr{background:#EF4444}
  .dim-bar-stab{background:#10B981}
  .dim-bar-calib{background:#8B5CF6}
  .dim-bar-igap{background:#06B6D4}
  .dim-bar-hflr{background:#F97316}
  .dim-bar-xdept{background:#EC4899}
  .dim-bar-trace{background:#84CC16}
  @media(max-width:900px){.grid{grid-template-columns:1fr}.overall-score{font-size:1.8rem}}
</style>
</head>
<body>
<header>
  <h1>⚡ OPERATION NEXAAI <span id="scenario-badge" class="badge badge-h0">H0</span></h1>
  <div class="sub">EU AI Act Compliance Simulation — Live Competitive Scoreboard</div>
</header>
<div class="meta">
  <span><b id="live-time">--:--:--</b> &nbsp;<span class="live-dot"></span>LIVE</span>
  <span>Market Share Available: <b id="market-share">100%</b></span>
  <span>Scrutiny: <b id="scrutiny">MEDIUM</b></span>
  <span>HireBot: <b id="hirebot">NOT LAUNCHED</b></span>
</div>

<div class="grid" id="company-grid">
  <!-- filled by JS -->
</div>

<div class="ticker" id="ticker">Loading market data...</div>

<script>
const TEAMS = ["team_a","team_b","team_c","team_d"];
const NAMES = {team_a:"VeriHire AI",team_b:"TalentLens",team_c:"ClearPath AI",team_d:"NexaRecruit"};
const DIM_LABELS = {
  incommensurability:"Incomm",contradiction:"Contr",stability:"Stable",
  calibration:"Calib",info_gap:"InfoGap",hard_floor:"HFloor",
  cross_dept:"XDept",traceability:"Trace"
};
const DIM_MAX = {
  incommensurability:18,contradiction:18,stability:18,calibration:12,
  info_gap:12,hard_floor:10,cross_dept:7,traceability:5
};
const DIM_COLOR = {
  incommensurability:"F59E0B",contradiction:"EF4444",stability:"10B981",
  calibration:"8B5CF6",info_gap:"06B6D4",hard_floor:"F97316",
  cross_dept:"EC4899",traceability:"84CC16"
};

function scoreColor(pct){
  if(pct>=70) return "#10B981";
  if(pct>=45) return "#F59E0B";
  return "#EF4444";
}

function renderGrid(data){
  const grid = document.getElementById("company-grid");
  grid.innerHTML = "";
  const sorted = [...TEAMS].sort((a,b)=>(data[b]?.overall||0)-(data[a]?.overall||0));
  sorted.forEach(tid=>{
    const s = data[tid] || {};
    const overall = s.overall || 0;
    const dims = s.dimensions || {};
    const penalty = s.penalty || 0;
    const ms = (s.market_share||1.0)*100;
    const card = document.createElement("div");
    card.className="card"; card.dataset.team=tid;

    const dimHTML = Object.entries(DIM_LABELS).map(([k,label])=>{
      const val = dims[k]||0;
      const max = DIM_MAX[k];
      const pct = max>0?(val/max*100):0;
      return `<div class="dim">
        <div class="dim-label">${label}</div>
        <div class="dim-bar-wrap"><div class="dim-bar" style="width:${pct}%;background:#${DIM_COLOR[k]}"></div></div>
        <div class="dim-val">${val}/${max}</div>
      </div>`;
    }).join("");

    card.innerHTML = `
      <div class="card-header">
        <div>
          <div class="company-name">${NAMES[tid]}</div>
          <div class="sub-info">
            <span>Sub #${s.submission_count||0}</span>
            <span>Scenario: ${s.scenario||"H0"}</span>
            ${s.last_submission?`<span>${s.last_submission.substring(11,16)}</span>`:""}
          </div>
        </div>
        <div style="text-align:right">
          <div class="overall-score" style="color:${scoreColor(overall)}">${overall.toFixed(1)}<span style="font-size:1.2rem;color:#9CA3AF">%</span></div>
          <div class="score-label">Overall Score</div>
          ${penalty>0?`<div class="penalty-badge">-${Math.round(penalty*100)}% penalty</div>`:""}
        </div>
      </div>
      <div class="dims">${dimHTML}</div>
      <div class="market-bar">
        <div class="market-label">EU Market Share: ${ms.toFixed(0)}%</div>
        <div class="market-share-bar"><div class="market-share-fill" style="width:${ms}%"></div></div>
      </div>`;
    grid.appendChild(card);
  });
}

async function refresh(){
  try{
    const r = await fetch("/api/scores");
    const d = await r.json();
    renderGrid(d.scores);
    document.getElementById("live-time").textContent = d.last_updated||"--";
    // Update badges
    const sc = d.scenario||"H0";
    const badge = document.getElementById("scenario-badge");
    badge.textContent=sc; badge.className=`badge badge-${sc.toLowerCase()}`;
    const m=d.market||{};
    document.getElementById("market-share").textContent=((m.eu_available_market_share||1)*100).toFixed(0)+"%";
    document.getElementById("scrutiny").textContent=m.regulatory_scrutiny_level||"MEDIUM";
    document.getElementById("hirebot").textContent=m.hirebot_eu_status||"NOT LAUNCHED";
    // Ticker
    const tick=[];
    if(m.deutsche_bank_status) tick.push(`Deutsche Bank: <b>${m.deutsche_bank_status}</b>`);
    if(m.hirebot_threat_score) tick.push(`HireBot Threat: <b>${(m.hirebot_threat_score*100).toFixed(0)}%</b>`);
    if(m.market_window_months) tick.push(`Market Window: <b>${m.market_window_months} months</b>`);
    if(m.personal_liability_active) tick.push(`<b style="color:#FCA5A5">⚠ Personal Liability ACTIVE</b>`);
    if(m.emergency_directive_active) tick.push(`<b style="color:#FCA5A5">🚨 Emergency Directive 2026/447 ACTIVE</b>`);
    if(d.log&&d.log[0]) tick.push(`Last: <b>${d.log[0]}</b>`);
    document.getElementById("ticker").innerHTML=tick.map(t=>`<span class="tick-item">${t}</span>`).join(" &nbsp;·&nbsp; ")||"Market data loading...";
  }catch(e){console.error(e)}
}
refresh();
setInterval(refresh,6000);
</script>
</body>
</html>"""

# ── INSTRUCTOR CONTROL PANEL ──────────────────────────────────────────

CONTROL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NexaAI — Instructor Control</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#0F172A;color:#F1F5F9;font-family:'Segoe UI',system-ui,sans-serif;padding:16px}
  h1{font-size:1.5rem;font-weight:700;margin-bottom:4px}
  .sub{color:#94A3B8;font-size:.85rem;margin-bottom:20px}
  a.link{color:#60A5FA;text-decoration:none;font-size:.85rem}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .panel{background:#1E293B;border:1px solid #334155;border-radius:10px;padding:16px}
  .panel h2{font-size:1rem;font-weight:700;margin-bottom:12px;color:#CBD5E1;border-bottom:1px solid #334155;padding-bottom:8px}
  .btn{padding:8px 16px;border:none;border-radius:6px;font-size:.85rem;font-weight:600;cursor:pointer;transition:.15s}
  .btn:hover{opacity:.85} .btn:active{transform:scale(.97)}
  .btn-primary{background:#3B82F6;color:#fff}
  .btn-green{background:#10B981;color:#fff}
  .btn-amber{background:#F59E0B;color:#000}
  .btn-red{background:#EF4444;color:#fff}
  .btn-purple{background:#8B5CF6;color:#fff}
  .btn-sm{padding:5px 10px;font-size:.78rem}
  .hurdle-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:8px}
  .team-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
  .team-card{background:#0F172A;border:1px solid #334155;border-radius:6px;padding:10px}
  .team-card h3{font-size:.85rem;font-weight:700;margin-bottom:6px}
  .score-big{font-size:1.6rem;font-weight:800}
  .score-sm{font-size:.72rem;color:#94A3B8}
  table{width:100%;border-collapse:collapse;font-size:.78rem;margin-top:8px}
  th{text-align:left;padding:6px 8px;background:#0F172A;color:#94A3B8;font-weight:600}
  td{padding:5px 8px;border-bottom:1px solid #1E293B}
  tr:hover td{background:#1E293B}
  input{background:#0F172A;border:1px solid #334155;color:#F1F5F9;padding:6px 10px;border-radius:5px;font-size:.82rem;width:100%;margin-bottom:8px}
  .log-box{background:#0F172A;border-radius:6px;padding:10px;font-size:.72rem;color:#94A3B8;font-family:monospace;height:140px;overflow-y:auto;margin-top:8px}
  .tag{padding:2px 7px;border-radius:99px;font-size:.68rem;font-weight:700}
  .tag-h0{background:#374151;color:#D1D5DB}
  .tag-h1{background:#78350F;color:#FDE68A}
  .tag-h2{background:#064E3B;color:#6EE7B7}
  .tag-h3{background:#7F1D1D;color:#FCA5A5}
  .status-dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px}
  .dot-green{background:#10B981}.dot-red{background:#EF4444}.dot-amber{background:#F59E0B}
  .flash{animation:flash .4s ease}
  @keyframes flash{0%{opacity:1}50%{opacity:.2}100%{opacity:1}}
  .config-row{display:flex;gap:8px;align-items:center;margin-bottom:8px}
  .config-row label{font-size:.78rem;color:#94A3B8;white-space:nowrap;width:120px}
  .config-row input{margin:0}
</style>
</head>
<body>
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px">
  <div>
    <h1>🎛️ Instructor Control Panel — NexaAI</h1>
    <div class="sub">Private panel · <a class="link" href="/" target="_blank">Open Scoreboard ↗</a></div>
  </div>
  <div style="font-size:.8rem;color:#94A3B8">
    RAG: <span id="rag-url" style="color:#60A5FA">{{rag_url}}</span><br>
    <span id="rag-status">checking...</span>
  </div>
</div>

<div class="grid">
  <!-- LEFT COLUMN -->
  <div style="display:flex;flex-direction:column;gap:16px">

    <!-- Scenario -->
    <div class="panel">
      <h2>🎯 Scenario Control</h2>
      <div style="margin-bottom:10px;font-size:.85rem">Active: <span id="current-scenario" class="tag tag-h0">H0</span></div>
      <div class="hurdle-grid">
        <button class="btn btn-amber" onclick="injectHurdle('H1')">⚡ Inject H1<br><small>HireBot Challenge</small></button>
        <button class="btn btn-green" onclick="injectHurdle('H2')">💼 Inject H2<br><small>Deutsche Bank</small></button>
        <button class="btn btn-red" onclick="injectHurdle('H3')">🚨 Inject H3<br><small>Emergency Dir.</small></button>
      </div>
      <div id="hurdle-msg" style="margin-top:8px;font-size:.78rem;color:#6EE7B7;min-height:18px"></div>
    </div>

    <!-- Market Editor -->
    <div class="panel">
      <h2>📊 Market Parameters</h2>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
        <div>
          <div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">EU Market Share (0-1)</div>
          <input id="mkt-share" type="number" min="0" max="1" step="0.01" placeholder="0.88">
        </div>
        <div>
          <div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">HireBot Threat (0-1)</div>
          <input id="mkt-hirebot" type="number" min="0" max="1" step="0.01" placeholder="0.45">
        </div>
        <div>
          <div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">Scrutiny Level</div>
          <input id="mkt-scrutiny" type="text" placeholder="MEDIUM">
        </div>
        <div>
          <div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">Market Window (months)</div>
          <input id="mkt-window" type="number" step="0.5" placeholder="6.0">
        </div>
      </div>
      <button class="btn btn-primary btn-sm" style="margin-top:8px" onclick="pushMarket()">⬆ Push to RAG</button>
      <div id="market-msg" style="margin-top:6px;font-size:.78rem;color:#6EE7B7;min-height:16px"></div>
    </div>

    <!-- Push Competitor Bulletin -->
    <div class="panel">
      <h2>📢 Push Competitor Bulletin</h2>
      <div style="font-size:.72rem;color:#94A3B8;margin-bottom:4px">Simulates a competitor release visible to all teams</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px">
        <div><div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">Company</div>
          <input id="bul-company" placeholder="TalentLens (team_b)"></div>
        <div><div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">Overall Score</div>
          <input id="bul-score" type="number" placeholder="54.2"></div>
      </div>
      <div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">Market consequences (one per line: key: value)</div>
      <textarea id="bul-market" rows="3" style="background:#0F172A;border:1px solid #334155;color:#F1F5F9;padding:6px 10px;border-radius:5px;font-size:.78rem;width:100%;resize:none" placeholder="eu_available_market_share: 0.88&#10;hirebot_threat_score: 0.52"></textarea>
      <button class="btn btn-purple btn-sm" style="margin-top:8px" onclick="pushBulletin()">📤 Push Bulletin</button>
      <div id="bul-msg" style="margin-top:6px;font-size:.78rem;color:#6EE7B7;min-height:16px"></div>
    </div>

  </div>

  <!-- RIGHT COLUMN -->
  <div style="display:flex;flex-direction:column;gap:16px">

    <!-- Submission Management -->
    <div class="panel">
      <h2>📥 Submissions</h2>
      <div class="team-grid" id="team-status">loading...</div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-green" onclick="collectAll()">🔄 Collect All Submissions</button>
        <button class="btn btn-primary" onclick="processAll()">📊 Recalculate Scores</button>
        <button class="btn btn-purple btn-sm" onclick="pushScoreboard()">⬆ Push Scoreboard to RAG</button>
      </div>
      <div id="collect-msg" style="margin-top:6px;font-size:.78rem;color:#6EE7B7;min-height:16px"></div>

      <table id="sub-table">
        <thead><tr><th>Team</th><th>Sub#</th><th>Scenario</th><th>Score</th><th>Penalty</th><th>Time</th></tr></thead>
        <tbody id="sub-rows"><tr><td colspan="6" style="color:#64748B;padding:12px">No submissions collected yet</td></tr></tbody>
      </table>
    </div>

    <!-- Score Override -->
    <div class="panel">
      <h2>✏️ Manual Score Override</h2>
      <div style="font-size:.72rem;color:#94A3B8;margin-bottom:8px">Override overall score for a team (bypasses auto-calculation)</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px">
        <div><div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">Team</div>
          <select id="ov-team" style="background:#0F172A;border:1px solid #334155;color:#F1F5F9;padding:6px;border-radius:5px;width:100%;font-size:.82rem">
            <option value="team_a">VeriHire AI</option>
            <option value="team_b">TalentLens</option>
            <option value="team_c">ClearPath AI</option>
            <option value="team_d">NexaRecruit</option>
          </select></div>
        <div><div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">Dimension</div>
          <select id="ov-dim" style="background:#0F172A;border:1px solid #334155;color:#F1F5F9;padding:6px;border-radius:5px;width:100%;font-size:.82rem">
            <option value="overall">Overall %</option>
            <option value="incommensurability">Incomm /18</option>
            <option value="contradiction">Contradiction /18</option>
            <option value="stability">Stability /18</option>
            <option value="calibration">Calibration /12</option>
            <option value="info_gap">Info Gap /12</option>
            <option value="hard_floor">Hard Floor /10</option>
            <option value="cross_dept">Cross Dept /7</option>
            <option value="traceability">Traceability /5</option>
          </select></div>
        <div><div style="font-size:.72rem;color:#94A3B8;margin-bottom:3px">Value</div>
          <input id="ov-val" type="number" placeholder="0-100"></div>
      </div>
      <button class="btn btn-amber btn-sm" style="margin-top:8px" onclick="applyOverride()">Apply Override</button>
      <div id="ov-msg" style="margin-top:6px;font-size:.78rem;color:#FDE68A;min-height:16px"></div>
    </div>

    <!-- Config -->
    <div class="panel">
      <h2>⚙️ Config</h2>
      <div class="config-row"><label>RAG Server URL</label><input id="cfg-rag" value="{{rag_url}}"></div>
      <div class="config-row"><label>Team A IP</label><input id="cfg-team-a" value="{{team_a_ip}}"></div>
      <div class="config-row"><label>Team B IP</label><input id="cfg-team-b" value="{{team_b_ip}}"></div>
      <div class="config-row"><label>Team C IP</label><input id="cfg-team-c" value="{{team_c_ip}}"></div>
      <div class="config-row"><label>Team D IP</label><input id="cfg-team-d" value="{{team_d_ip}}"></div>
      <button class="btn btn-primary btn-sm" onclick="updateConfig()">Save Config</button>
      <div id="cfg-msg" style="margin-top:6px;font-size:.78rem;color:#6EE7B7;min-height:16px"></div>
    </div>

  </div>
</div>

<!-- Log -->
<div style="margin-top:16px;background:#1E293B;border:1px solid #334155;border-radius:10px;padding:16px">
  <h2 style="font-size:.95rem;font-weight:700;color:#CBD5E1;margin-bottom:8px">📋 Event Log</h2>
  <div class="log-box" id="log-box">Loading...</div>
</div>

<script>
async function api(path, method="GET", body=null){
  const opts = {method, headers:{"Content-Type":"application/json"}};
  if(body) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  return r.json();
}
function msg(id, text, color="#6EE7B7"){
  const el=document.getElementById(id);
  el.style.color=color; el.textContent=text;
  setTimeout(()=>el.textContent="",5000);
}

async function injectHurdle(h){
  if(!confirm(`Inject ${h}? This changes the active scenario for ALL teams.`)) return;
  const d = await api(`/api/inject/${h}`, "POST");
  msg("hurdle-msg", d.message||d.error, d.ok?"#6EE7B7":"#FCA5A5");
}

async function pushMarket(){
  const updates={};
  const share=document.getElementById("mkt-share").value;
  const hb=document.getElementById("mkt-hirebot").value;
  const sc=document.getElementById("mkt-scrutiny").value;
  const wn=document.getElementById("mkt-window").value;
  if(share) updates.eu_available_market_share=parseFloat(share);
  if(hb) updates.hirebot_threat_score=parseFloat(hb);
  if(sc) updates.regulatory_scrutiny_level=sc;
  if(wn) updates.market_window_months=parseFloat(wn);
  const d=await api("/api/update_market","POST",updates);
  msg("market-msg", d.message||d.error, d.ok?"#6EE7B7":"#FCA5A5");
}

async function pushBulletin(){
  const company=document.getElementById("bul-company").value;
  const score=parseFloat(document.getElementById("bul-score").value)||0;
  const raw=document.getElementById("bul-market").value;
  const market_updates={};
  raw.split("\\n").forEach(l=>{
    const [k,...v]=l.split(":");
    if(k&&v.length) market_updates[k.trim()]=isNaN(v.join(":").trim())?v.join(":").trim():parseFloat(v.join(":").trim());
  });
  const d=await api("/api/push_bulletin","POST",{company,score,market_updates});
  msg("bul-msg", d.message||d.error, d.ok?"#6EE7B7":"#FCA5A5");
}

async function collectAll(){
  msg("collect-msg","Collecting via SSH... (may take 15s)","#FDE68A");
  const d=await api("/api/collect","POST");
  msg("collect-msg", d.message||d.error, d.ok?"#6EE7B7":"#FCA5A5");
  refreshData();
}

async function processAll(){
  const d=await api("/api/process","POST");
  msg("collect-msg", d.message||d.error);
  refreshData();
}

async function pushScoreboard(){
  const d=await api("/api/push_scoreboard","POST");
  msg("collect-msg", d.message||d.error, d.ok?"#6EE7B7":"#FCA5A5");
}

async function applyOverride(){
  const team=document.getElementById("ov-team").value;
  const dim=document.getElementById("ov-dim").value;
  const val=parseFloat(document.getElementById("ov-val").value);
  const d=await api("/api/override","POST",{team,dimension:dim,value:val});
  msg("ov-msg", d.message||d.error, d.ok?"#FDE68A":"#FCA5A5");
  refreshData();
}

async function updateConfig(){
  const cfg={
    rag_url: document.getElementById("cfg-rag").value,
    team_ips: {
      team_a: document.getElementById("cfg-team-a").value,
      team_b: document.getElementById("cfg-team-b").value,
      team_c: document.getElementById("cfg-team-c").value,
      team_d: document.getElementById("cfg-team-d").value,
    }
  };
  const d=await api("/api/config","POST",cfg);
  msg("cfg-msg", d.message||d.error);
}

async function refreshData(){
  const d=await api("/api/scores");
  // Team cards
  const tc=document.getElementById("team-status");
  const NAMES={team_a:"VeriHire AI",team_b:"TalentLens",team_c:"ClearPath AI",team_d:"NexaRecruit"};
  tc.innerHTML=Object.entries(d.scores).map(([tid,s])=>`
    <div class="team-card">
      <h3>${NAMES[tid]}</h3>
      <div class="score-big" style="color:${s.overall>50?'#10B981':s.overall>25?'#F59E0B':'#EF4444'}">${s.overall.toFixed(1)}%</div>
      <div class="score-sm">Sub #${s.submission_count||0}${s.penalty>0?` · -${Math.round(s.penalty*100)}% pen`:''}</div>
    </div>`).join("");
  // Sub table
  const rows=document.getElementById("sub-rows");
  if(d.submissions&&d.submissions.length){
    rows.innerHTML=d.submissions.slice(0,15).map(s=>`
      <tr>
        <td>${NAMES[s._team_id]||s.company_id}</td>
        <td>${s.submission_number||"?"}</td>
        <td><span class="tag tag-${(s.active_scenario_id||'h0').toLowerCase()}">${s.active_scenario_id||"?"}</span></td>
        <td>${d.scores[s._team_id]?.overall?.toFixed(1)||"—"}%</td>
        <td>${d.scores[s._team_id]?.penalty>0?'-'+Math.round((d.scores[s._team_id]?.penalty||0)*100)+'%':"None"}</td>
        <td>${(s.submission_timestamp||"").substring(11,16)||"—"}</td>
      </tr>`).join("");
  }
  // Scenario
  const scBadge=document.getElementById("current-scenario");
  if(scBadge){scBadge.textContent=d.scenario||"H0";scBadge.className=`tag tag-${(d.scenario||"h0").toLowerCase()}`}
  // Log
  document.getElementById("log-box").innerHTML=(d.log||[]).join("<br>")||"No events yet";
  // RAG status
  const ragStatus=document.getElementById("rag-status");
  if(d.last_updated){ragStatus.innerHTML=`<span class="status-dot dot-green"></span>Connected · ${d.last_updated}`}
  else{ragStatus.innerHTML=`<span class="status-dot dot-red"></span>Disconnected`}
}

refreshData();
setInterval(refreshData, 6000);
</script>
</body>
</html>"""

# ── API ROUTES ────────────────────────────────────────────────────────

@app.route("/")
def scoreboard():
    return render_template_string(SCOREBOARD_HTML)

@app.route("/control")
def control():
    ips = TEAM_IP_MAP
    return render_template_string(CONTROL_HTML,
        rag_url=RAG_URL,
        team_a_ip=ips.get("team_a",""),
        team_b_ip=ips.get("team_b",""),
        team_c_ip=ips.get("team_c",""),
        team_d_ip=ips.get("team_d",""),
    )

@app.route("/api/scores")
def api_scores():
    with state_lock:
        return jsonify({
            "scores":       dict(state["scores"]),
            "market":       dict(state["market"]),
            "scenario":     state["scenario"],
            "last_updated": state["last_updated"],
            "submissions":  state["submissions"][:20],
            "log":          state["log"][:20],
        })

@app.route("/api/inject/<hurdle_id>", methods=["POST"])
def api_inject(hurdle_id):
    ok, msg_text = inject_hurdle(hurdle_id.upper())
    return jsonify({"ok": ok, "message": msg_text})

@app.route("/api/update_market", methods=["POST"])
def api_update_market():
    updates = request.json or {}
    try:
        resp = requests.get(f"{RAG_URL}/rag/all", timeout=5)
        files = resp.json()
        market = json.loads(files.get("market/market_state.json","{}"))
        market.update(updates)
        market["last_manual_update"] = datetime.now().isoformat()
        push_resp = requests.post(f"{RAG_URL}/push",
            json={"path":"market/market_state.json","content":json.dumps(market,indent=2)}, timeout=5)
        log(f"Market updated: {list(updates.keys())}")
        refresh_from_rag()
        return jsonify({"ok":True,"message":f"Market updated: {', '.join(updates.keys())}"})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)})

@app.route("/api/push_bulletin", methods=["POST"])
def api_push_bulletin():
    data = request.json or {}
    company = data.get("company","Unknown")
    score   = data.get("score",0)
    market_updates = data.get("market_updates",{})
    ts = datetime.now().strftime("%H:%M")
    bulletin_num = len(list(Path(SUBMISSIONS_DIR).glob("release_bulletin_*.md"))) + 1

    lines = [
        f"# MARKET BULLETIN — Release #{bulletin_num:03d}",
        f"# Time: {ts}  |  Company: {company}",
        f"",
        f"## Evaluation Score",
        f"  WEIGHTED AVERAGE: {score}/100",
        "",
        "## Market Consequences (Effective Now)",
    ]
    for k,v in market_updates.items():
        lines.append(f"  {k}: {v}")

    content = "\n".join(lines)
    path = f"releases/release_bulletin_{bulletin_num:03d}.md"

    try:
        requests.post(f"{RAG_URL}/push", json={"path":path,"content":content}, timeout=5)
        if market_updates:
            resp = requests.get(f"{RAG_URL}/rag/all", timeout=5)
            market = json.loads(resp.json().get("market/market_state.json","{}"))
            market.update(market_updates)
            requests.post(f"{RAG_URL}/push",
                json={"path":"market/market_state.json","content":json.dumps(market,indent=2)}, timeout=5)
            refresh_from_rag()
        log(f"Bulletin pushed: {company} score={score}")
        return jsonify({"ok":True,"message":f"Bulletin {bulletin_num:03d} published"})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)})

@app.route("/api/collect", methods=["POST"])
def api_collect():
    threading.Thread(target=_collect_bg, daemon=True).start()
    return jsonify({"ok":True,"message":"Collection started (SSH rsync). Check log in ~15s."})

def _collect_bg():
    collect_all()
    process_submissions()
    push_scoreboard_to_rag()

@app.route("/api/process", methods=["POST"])
def api_process():
    process_submissions()
    push_scoreboard_to_rag()
    return jsonify({"ok":True,"message":"Scores recalculated and pushed to RAG"})

@app.route("/api/push_scoreboard", methods=["POST"])
def api_push_scoreboard():
    push_scoreboard_to_rag()
    return jsonify({"ok":True,"message":"Scoreboard pushed to Global RAG"})

@app.route("/api/override", methods=["POST"])
def api_override():
    data   = request.json or {}
    team   = data.get("team","")
    dim    = data.get("dimension","overall")
    value  = float(data.get("value",0))
    if team not in TEAM_IDS:
        return jsonify({"ok":False,"error":"Unknown team"})
    with state_lock:
        if dim == "overall":
            state["scores"][team]["overall"] = value
        else:
            state["scores"][team]["dimensions"][dim] = int(value)
            # Recalculate overall
            dims   = state["scores"][team]["dimensions"]
            max_sc = {"incommensurability":18,"contradiction":18,"stability":18,"calibration":12,
                      "info_gap":12,"hard_floor":10,"cross_dept":7,"traceability":5}
            wts    = {"incommensurability":0.18,"contradiction":0.18,"stability":0.18,"calibration":0.12,
                      "info_gap":0.12,"hard_floor":0.10,"cross_dept":0.07,"traceability":0.05}
            pct = sum((dims.get(k,0)/max_sc[k])*wts[k] for k in max_sc)*100
            penalty = state["scores"][team]["penalty"]
            state["scores"][team]["overall"] = round(pct*(1-penalty),1)
    log(f"Manual override: {team} {dim}={value}")
    push_scoreboard_to_rag()
    return jsonify({"ok":True,"message":f"{TEAM_NAMES[team]} {dim} → {value}"})

@app.route("/api/config", methods=["POST"])
def api_config():
    global RAG_URL, TEAM_IP_MAP
    data = request.json or {}
    if "rag_url" in data:
        RAG_URL = data["rag_url"]
    if "team_ips" in data:
        for tid, ip in data["team_ips"].items():
            if ip:
                TEAM_IP_MAP[tid] = ip
    log(f"Config updated: RAG={RAG_URL}, IPs={TEAM_IP_MAP}")
    return jsonify({"ok":True,"message":"Config saved. Changes take effect immediately."})

# Also accept submission push from team machines (alternative to SSH pull)
@app.route("/api/submit", methods=["POST"])
def api_receive_submission():
    """Team machines can POST submissions directly here (avoids SSH)."""
    sub = request.json
    if not sub:
        return jsonify({"ok":False,"error":"No data"}), 400
    team_id = sub.get("company_id","unknown")
    sub_num = sub.get("submission_number",0)
    ts      = datetime.now().strftime("%H%M%S")
    dest_dir = SUBMISSIONS_DIR / team_id
    dest_dir.mkdir(exist_ok=True, parents=True)
    filename = f"submission_{team_id}_{sub_num:02d}_{ts}.json"
    (dest_dir / filename).write_text(json.dumps(sub, indent=2))
    log(f"Received submission: {team_id} #{sub_num}")
    process_submissions()
    push_scoreboard_to_rag()
    return jsonify({"ok":True,"message":f"Submission {filename} received and scored"})

if __name__ == "__main__":
    refresh_from_rag()
    print(f"""
╔══════════════════════════════════════════════════╗
║  NEXAAI INSTRUCTOR DASHBOARD                     ║
║  RAG Server:  {RAG_URL:<35}║
║  Team IPs:    {', '.join(TEAM_IPS):<35}║
╠══════════════════════════════════════════════════╣
║  📺 Scoreboard (projector):                      ║
║     http://localhost:{args.port}/                        ║
║  🎛️  Instructor panel:                           ║
║     http://localhost:{args.port}/control                 ║
╚══════════════════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)
