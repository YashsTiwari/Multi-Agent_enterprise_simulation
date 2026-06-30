#!/usr/bin/env python3
"""
NexaAI Instructor Dashboard - Clean working version
"""

import argparse
import requests
from flask import Flask, render_template_string, request, redirect
from datetime import datetime

app = Flask(__name__)
RAG_URL = "http://localhost:8888"   # default, will be overwritten by --rag

HTML = """<!DOCTYPE html>
<html><head><title>NexaAI Instructor Dashboard</title>
<meta http-equiv="refresh" content="30">
<style>
body { font-family: system-ui; margin:40px; background:#f8f9fa; }
h1 { color:#1a365d; }
.card { background:white; padding:24px; margin:20px 0; border-radius:10px; box-shadow:0 4px 6px rgba(0,0,0,0.07); }
button { padding:12px 24px; margin:8px; font-size:15px; font-weight:600; border:none; border-radius:6px; cursor:pointer; color:white; }
.btn-h1 { background:#e53e3e; }
.btn-h2 { background:#dd6b20; }
.btn-h3 { background:#d69e2e; }
pre { background:#1a202c; color:#e2e8f0; padding:16px; border-radius:8px; overflow-x:auto; font-size:13px; }
.status { color:#4a5568; }
.success { color:#38a169; font-weight:600; }
</style></head>
<body>
<h1>🎛️ NexaAI Instructor Dashboard</h1>
<p class="status">RAG: <strong>{{ rag_url }}</strong> | {{ now }}</p>

<div class="card">
<h2>🚨 Inject Hurdle</h2>
<form method="post" action="/inject">
<button type="submit" name="hurdle" value="H1" class="btn-h1">H1 — HireBot Challenge</button>
<button type="submit" name="hurdle" value="H2" class="btn-h2">H2 — Deutsche Bank Contract</button>
<button type="submit" name="hurdle" value="H3" class="btn-h3">H3 — Emergency Directive</button>
</form>
{% if message %}<p class="success">{{ message }}</p>{% endif %}
</div>

<div class="card">
<h2>Current Market State</h2>
<pre>{{ market_state }}</pre>
</div>

<div class="card">
<h2>Active Scenario</h2>
<pre>{{ active_scenario[:1000] }}...</pre>
</div>
</body></html>"""

@app.route("/")
def index():
    message = request.args.get("message", "")
    try:
        r = requests.get(f"{RAG_URL}/rag/all", timeout=5)
        files = r.json()
        market = files.get("market/market_state.json", "{}")
        scenario = files.get("scenario/active_scenario.md", "No scenario")
    except Exception as e:
        market = f'{{"error": "{e}"}}'
        scenario = "Could not reach RAG server"

    return render_template_string(HTML, rag_url=RAG_URL, now=datetime.now().strftime("%H:%M:%S"),
                                  market_state=market, active_scenario=scenario, message=message)

@app.route("/inject", methods=["POST"])
def inject():
    hurdle = request.form.get("hurdle")
    if hurdle in ["H1","H2","H3"]:
        try:
            requests.post(f"{RAG_URL}/push/hurdle/{hurdle}", timeout=8)
            return redirect(f"/?message=✅ {hurdle} injected successfully")
        except Exception as e:
            return redirect(f"/?message=❌ Failed: {e}")
    return redirect("/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rag", default="http://localhost:8888")
    args = parser.parse_args()
    global RAG_URL
    RAG_URL = args.rag.rstrip("/")
    print(f"Dashboard started → RAG: {RAG_URL}")
    app.run(host="0.0.0.0", port=8080, debug=False)
