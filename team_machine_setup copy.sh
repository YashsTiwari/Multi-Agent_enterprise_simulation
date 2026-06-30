instructor_dashboard.py#!/usr/bin/env python3
"""
Simple, reliable instructor dashboard for Operation NexaAI
Run with: python3 instructor_dashboard.py --rag http://IP:8888
"""

import argparse
import requests
from flask import Flask, render_template_string, request, jsonify, redirect
from datetime import datetime

app = Flask(__name__)

RAG_URL = "http://localhost:8888"

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>NexaAI Instructor Dashboard</title>
    <style>
        body { font-family: system-ui; margin: 40px; background: #f8f9fa; }
        h1 { color: #1a365d; }
        .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; }
        .btn-h1 { background: #e53e3e; color: white; border: none; }
        .btn-h2 { background: #dd6b20; color: white; border: none; }
        .btn-h3 { background: #d69e2e; color: white; border: none; }
        pre { background: #1a202c; color: #e2e8f0; padding: 15px; border-radius: 6px; overflow-x: auto; }
        .status { font-size: 14px; color: #4a5568; }
    </style>
</head>
<body>
    <h1>🎛️ NexaAI Instructor Dashboard</h1>
    <p class="status">RAG Server: {{ rag_url }} | Last updated: {{ now }}</p>

    <div class="card">
        <h2>Inject Hurdles</h2>
        <form method="post" action="/inject">
            <button type="submit" name="hurdle" value="H1" class="btn-h1">Inject H1 (HireBot Challenge)</button>
            <button type="submit" name="hurdle" value="H2" class="btn-h2">Inject H2 (Deutsche Bank Contract)</button>
            <button type="submit" name="hurdle" value="H3" class="btn-h3">Inject H3 (Emergency Directive)</button>
        </form>
    </div>

    <div class="card">
        <h2>Current Market State</h2>
        <pre>{{ market_state }}</pre>
    </div>

    <div class="card">
        <h2>Active Scenario</h2>
        <pre>{{ active_scenario[:800] }}...</pre>
    </div>

    <div class="card">
        <h2>Quick Actions</h2>
        <a href="/status"><button>Check RAG Status</button></a>
        <a href="{{ rag_url }}/rag/all" target="_blank"><button>View All RAG Files</button></a>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    try:
        r = requests.get(f"{RAG_URL}/rag/all", timeout=5)
        files = r.json()
        market = files.get("market/market_state.json", "{}")
        scenario = files.get("scenario/active_scenario.md", "No scenario yet")
    except Exception as e:
        market = f"Error: {e}"
        scenario = "Could not fetch"

    return render_template_string(HTML,
        rag_url=RAG_URL,
        now=datetime.now().strftime("%H:%M:%S"),
        market_state=market,
        active_scenario=scenario
    )

@app.route("/inject", methods=["POST"])
def inject():
    hurdle = request.form.get("hurdle")
    if hurdle in ["H1", "H2", "H3"]:
        try:
            requests.post(f"{RAG_URL}/push/hurdle/{hurdle}", timeout=10)
        except Exception as e:
            return f"Failed to inject {hurdle}: {e}", 500
    return redirect("/")

@app.route("/status")
def status():
    try:
        r = requests.get(f"{RAG_URL}/status", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rag", default="http://localhost:8888")
    args = parser.parse_args()
    global RAG_URL
    RAG_URL = args.rag
    print(f"Starting instructor dashboard → RAG: {RAG_URL}")
    app.run(host="0.0.0.0", port=8080, debug=False)