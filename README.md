# Multi-Agent Enterprise Simulation

> **A 7-hour competitive workshop where student teams build complete AI-powered organisations that must make high-stakes strategic decisions under live regulatory and market pressure.**

This repository contains **everything** needed to run (or adapt) the simulation: starter code, infrastructure scripts, Global RAG server, evaluation engine, hurdle injection system, and all supporting materials.

**If you are reading this months or years later, or you have never seen this workshop before** — this single file + the code in the repo is designed to be sufficient. You should be able to understand the *what*, *why*, and *how* of every component and successfully run or fork the entire experience.

---

## Table of Contents

1. [What This Simulation Actually Is](#1-what-this-simulation-actually-is)
2. [Why This Was Built — The Pedagogical Philosophy](#2-why-this-was-built--the-pedagogical-philosophy)
3. [The Core Story & Decision Every Team Must Make](#3-the-core-story--decision-every-team-must-make)
4. [The Four Companies](#4-the-four-companies)
5. [System Architecture Overview](#5-system-architecture-overview)
6. [The Global RAG Server & Live Hurdle System](#6-the-global-rag-server--live-hurdle-system)
7. [How Teams Build Their Agents (The Student Side)](#7-how-teams-build-their-agents-the-student-side)
8. [The CEO Consensus Components (The Hardest & Most Important Part)](#8-the-ceo-consensus-components-the-hardest--most-important-part)
9. [Complete File-by-File Explanation](#9-complete-file-by-file-explanation)
10. [Data Flow & Execution Order (Non-Negotiable)](#10-data-flow--execution-order-non-negotiable)
11. [Complete Setup & Running Guide](#11-complete-setup--running-guide)
12. [How to Run the Workshop Day (Timeline + Operations)](#12-how-to-run-the-workshop-day-timeline--operations)
13. [The Three Hurdles — Detailed Mechanics](#13-the-three-hurdles--detailed-mechanics)
14. [Evaluation, Schema Validation & Scoring](#14-evaluation-schema-validation--scoring)
15. [Adapting This for Future Classes or Different Domains](#15-adapting-this-for-future-classes-or-different-domains)
16. [Troubleshooting & Common Failure Modes](#16-troubleshooting--common-failure-modes)
17. [Key Lessons from the First Run](#17-key-lessons-from-the-first-run)
18. [Credits](#18-credits)

---

## 1. What This Simulation Actually Is

This is **not** a typical AI coding workshop.

Instead of asking students to build a single chatbot, RAG app, or fine-tune a model, this workshop asks them to **build an entire AI-powered organisation** from scratch.

Each team of ~30–35 students is divided into six sub-teams:
- Finance (5–6 people)
- Engineering (5–6)
- Marketing (5–6)
- HR (5–6)
- Legal (5–6)
- CEO / Architecture (the remaining students)

Each sub-team builds **one specialised AI agent** (except CEO, who builds the coordination layer). These agents must:
- Read live shared market/regulatory data from a central server
- Use deterministic calculation tools (not just LLM guesses)
- Exchange critical information across departments
- Handle conflicting objectives and hard constraints
- Adapt when the external environment changes dramatically (via "hurdles")
- Produce one coherent organisational decision through a CEO consensus mechanism

The output of the entire system is a single JSON submission containing:
- Recommendations + reasoning from all five departments
- A final CEO decision (approve / conditional_approve / delay / veto + timeline)
- Full traceability of tools used, cross-department data passed, commitments checked, contradictions detected, calibration applied, etc.

**The simulation runs in multiple rounds with live "hurdle" injections** that change the scenario and market state in real time. Teams that hardcode values or build brittle agents get punished. Teams that build modular, RAG-reading, tool-using agents can adapt in minutes.

It is deliberately designed to feel like deploying AI inside a real enterprise under regulatory pressure (specifically modelled on the EU AI Act in 2026).

---

## 2. Why This Was Built — The Pedagogical Philosophy

Most AI education still teaches **isolated model capabilities**. Students learn prompting, RAG, agents, tool use, evaluation, etc., in separate exercises. This creates a dangerous illusion: that intelligence is a property of a single model.

In reality, **enterprise intelligence is an organisational property**. It emerges from:
- Specialised agents holding different private information
- Different optimisation objectives and risk tolerances
- Structured communication protocols
- Mechanisms for resolving incommensurable values (money vs risk vs feasibility vs brand vs legal exposure)
- Memory of past commitments and detection of contradictions when the world changes
- Continuous recalibration based on prediction accuracy

This simulation forces students to confront all of these realities simultaneously.

**Specific design goals:**
- Force **cross-department data dependencies** (HR → Engineering & Finance) so students experience why information sharing is hard and necessary.
- Make **hard constraints and vetoes** first-class citizens (Finance has a cash floor, Engineering has a bias reproduction floor, etc.).
- Require a **deterministic consensus layer** (CEO) so students learn that "just averaging" or "let the LLM decide" is insufficient.
- Use **live regulatory/market shocks** (hurdles) to teach the difference between brittle hardcoded systems and adaptive RAG + tool systems.
- Enforce **traceability and schema validation** so every decision can be audited — mirroring real enterprise governance requirements.

The EU AI Act hiring-tool scenario was chosen because it is timely, high-stakes, involves genuine trade-offs, and forces engagement with real regulatory text.

---

## 3. The Core Story & Decision Every Team Must Make

**Background (shared by all teams):**

Four AI startups have each developed an AI-powered hiring tool (CV screening, candidate ranking, bias detection). The product is already live and profitable in the US and UK. There is a waitlist of 500 EU enterprise customers. Investors expect a European launch.

One week before the workshop, the EU AI Act classified AI hiring tools as **HIGH RISK** under Article 6 + Annex III. This triggers a long list of compliance obligations (technical documentation Art. 11, human oversight Art. 14, EU database registration Art. 51, conformity assessment, etc.).

**The central question every company must answer in every round:**

> Should we launch in the EU in **30 days**, **90 days**, or **delay until Q3** (or later)?

There is **no clean answer**. Every department has different information, different constraints, and different risk tolerances. The CEO agent must synthesise everything into one defensible organisational decision.

The simulation runs through **four phases** (H0 baseline + three injected hurdles). Each hurdle changes both the narrative scenario and the live market parameters that all agents read from the Global RAG.

---

## 4. The Four Companies

All four companies face **identical** market conditions and receive the **same hurdles at the same time**. They differ only in their internal private knowledge (department handbooks) and in how well their agents are implemented.

| Team ID   | Company Name     | Typical Machine IP (example) | Code Editor URL                  | Notes |
|-----------|------------------|------------------------------|----------------------------------|-------|
| `team_a`  | VeriHire AI     | 172.18.40.114               | http://IP:8080 or 8090          | - |
| `team_b`  | TalentLens      | 172.18.40.111               | http://IP:8080                  | - |
| `team_c`  | ClearPath AI    | 172.18.40.115               | http://IP:8080                  | - |
| `team_d`  | NexaRecruit     | 172.18.40.116               | http://IP:8080                  | - |

**Important for future runs:** These IPs are from the first run. You **must** update `RAG_SERVER_URL` in every team's `config.py` and the IPs in `MASTER_SETUP.sh` / `start.sh`.

---

## 5. System Architecture Overview

There are two main sides:

### A. Instructor / Central Side (`mac_control/`)
- Runs on the instructor's machine (usually a Mac on the same LAN).
- **Global RAG Server** (`rag_server.py`): Flask server that serves a directory of Markdown and JSON files to all teams. Supports live updates and special "hurdle injection" endpoints.
- **Hurdle files** (`hurdles/H1.md`, `H2.md`, `H3.md`): Narrative text + market state changes.
- **instructor_cli.py**: Simple CLI for instructor to check status, inject hurdles, push updates, view scoreboard/market.
- Dashboard / scoreboard (web UI for live scores).

### B. Team Side (`team_machine/`)
Distributed to every team machine (or run locally by students).
- **Starter code** + skeleton files.
- Students implement:
  - 5 department agents (subclassing `DepartmentAgent`)
  - Deterministic Python **tools** for calculations
  - CEO coordination layer (`ValueConverter`, `ConsensusEngine`, `CommitmentLedger`, `CalibrationTracker`)
- Every run reads fresh data from the Global RAG (market state, active scenario, competitor releases, prediction accuracy reports, regulations).
- Produces a strictly validated JSON submission.

**Communication**: All team machines read from the single Global RAG server. No direct peer-to-peer communication between teams. Market consequences of one team's launch decision can be pushed by the instructor to affect everyone.

---

## 6. The Global RAG Server & Live Hurdle System

This is the **heart of the live simulation**.

**Location**: `mac_control/rag_server.py` (Flask on port **8888** by default).

**What it serves** (`mac_control/global_rag/`):
- `scenario/active_scenario.md` — Current active hurdle text (updated on every injection)
- `scenario/scenario_history.md` — Log of all injections
- `market/market_state.json` — Live parameters (market share, HireBot status, Deutsche Bank contract details, regulatory scrutiny level, personal liability flag, etc.)
- `releases/` — Competitor launch bulletins (pushed by instructor after good submissions)
- `regulation/` — EU AI Act summaries and updates
- `news/`, `scores/`, etc.

**Key endpoints**:
- `GET /rag/all` → Returns every `.md` and `.json` file (used by `global_rag_client.py`)
- `GET /status` → Health + current hash + file count
- `POST /push` → Push a file update
- `POST /push/hurdle/H1` (or H2/H3) → **The magic**. This:
  1. Overwrites `active_scenario.md` with the hurdle narrative
  2. Applies predefined market updates from `HURDLE_MARKET_UPDATES` dict inside `rag_server.py`
  3. Appends to history
  4. Returns new hash

**Why this design?**
Teams **must** call `read_global_rag_and_hash()` at the start of every agent run. The hash is included in every submission. This allows the evaluator to detect staleness (teams that hardcoded market values instead of reading live data).

The deterministic hashing logic (normalising line endings, sorting keys, using `||` separator) is duplicated in both server and client to prevent false positives from OS/editor differences.

---

## 7. How Teams Build Their Agents (The Student Side)

### Base Class: `agents/department_agent.py`

Every department agent inherits from this. It provides:
- `read_global_rag()` — **Must be the first line of `analyze()`**. Reads live data + stores hash.
- `read_private_rag()` — Reads department-specific private knowledge from `knowledge/{dept}/` (Markdown/JSON files that students populate from Handouts).
- `call_ollama(prompt, system)` — Calls the department's model and auto-increments `llm_calls_made`.
- `call_tool(tool_func, **kwargs)` — **Mandatory wrapper**. Calls a deterministic Python function and automatically logs it to `tools_called` + `tool_outputs`. This is how the schema validator knows tools were actually used.
- `get_output()` — Returns the full structured dict after validation.

### Pattern (see `example_finance_agent.py` for the full worked example)

```python
class FinanceAgent(DepartmentAgent):
    def __init__(self):
        super().__init__("finance")

    def analyze(self, scenario=""):
        self.read_global_rag()                    # Step 1: Always first
        private = self.read_private_rag()         # Step 2: Private handbook knowledge

        # Step 3: Call deterministic tools (with cross-dept inputs)
        burn = self.call_tool(self.calculate_burn_escalation, new_hires=..., hire_cost=...)
        contract = self.call_tool(self.evaluate_contract_decision, compliance_probability=...)

        # Step 4: LLM reasoning that cites tool outputs
        text = self.call_ollama(...)

        self._output = {
            "recommendation": "delay",
            "recommended_timeline": "90d",
            "stated_reasoning": "... Finance.calculate_burn_escalation returned runway_months=6.8 ...",
            "external_inputs_used": {"hr": "...", "engineering": "..."},
            "hard_floor_breached": False,
            "prediction": {...},
            # ... many more required fields
        }
```

### Tools
Students implement **pure Python functions** that return dicts (e.g. `calculate_burn_escalation`, `estimate_feasibility`, `model_fine_distribution`, `model_hiring_pipeline`, etc.). These live in `tools/` or inside the agent file. LLM calls are only for reasoning/synthesis — never for the actual numeric calculations.

### Private Knowledge
Each department gets private handbooks (from `Handouts/` company folders or separate dept PDFs). These contain numbers, constraints, and domain knowledge that other departments do **not** have. This creates realistic information asymmetry.

---

## 8. The CEO Consensus Components (The Hardest & Most Important Part)

The CEO layer is what turns five conflicting departmental recommendations into **one organisational decision**. This is deliberately the most complex part of the workshop.

Students must implement (or heavily extend) four components in `state/`, `converter/`, and `consensus/`:

### 1. ValueConverter (`converter/value_converter.py`)
Translates incommensurable outputs into a common unit + uncertainty ranges.
- Finance: EUR Net Present Value
- Legal: EUR expected fine exposure
- Engineering: feasibility probability (0–1)
- Marketing: market share points or brand score
- HR: weeks until effective FTE or burnout risk score

The converter must produce non-placeholder values and explicit uncertainty ranges. This is heavily weighted in scoring.

### 2. CommitmentLedger (`state/commitment_ledger.py`)
Records important past decisions with reversibility scores and conditions.
- Example: Accepting the Deutsche Bank €10M contract in H2 with 60-day go-live condition.
- In H3, the ledger detects that the new Emergency Directive makes the prior commitment impossible → contradiction flagged.

### 3. CalibrationTracker (`state/calibration_tracker.py`)
After each round, reads the prediction accuracy report from RAG (`scores/prediction_accuracy_round_X.md`) and updates per-department weights.
- Departments that were over-confident or systematically wrong get lower weight in future rounds.
- Weights must be non-uniform and sum to 1.0.

### 4. ConsensusEngine (`consensus/engine.py`)
The actual decision algorithm. It should be **deterministic** (same inputs → same output). It typically:
- Applies calibration weights
- Respects vetoes / hard floors
- Uses the ValueConverter outputs
- Checks the CommitmentLedger for contradictions
- Produces final recommendation + rich traceability fields

The `main.py` file contains extensive comments showing exactly how to wire these four components together.

---

## 9. Complete File-by-File Explanation

### Root Level
- `MASTER_SETUP.sh` — One-command setup for instructor Mac + SSH push to all team machines. Packages `team_machine/`, runs remote setup, starts RAG server, prints student URLs.
- `start.sh` — Simpler Mac startup (auto-detects IP, starts RAG + dashboard). Good for quick tests or single-machine runs.
- `team_machine_setup.sh` — Run on each team machine. Creates `~/nexaai/project/`, installs packages, pulls Ollama models, sets up code-server (port 8080, no auth), patches config, tests RAG connection.
- `instructor_dashboard.py` — Web dashboard (more feature-rich but sometimes less stable than simple alternatives).
- `team_machine_setup copy.sh` — Duplicate — safe to delete.

### `mac_control/`
- `rag_server.py` — The Global RAG Flask server. Contains the `HURDLE_MARKET_UPDATES` dict and hurdle injection logic.
- `global_rag/` — The actual served content (you populate scenario, market, hurdles, regulation, etc.).
- `hurdles/` — Source files for H1/H2/H3 narrative + market deltas.
- `instructor_cli.py` — CLI for `status`, `inject H1|H2|H3`, `push`, `scoreboard`, `market`, etc.
- `dashboard.py` — Alternative web dashboard.

### `team_machine/` (distributed to students)
- `main.py` — Orchestration script. Reads RAG, runs departments in correct order, runs CEO, assembles + submits JSON. Contains the most important documentation comments in the repo.
- `config.py` — Team identity (`TEAM_ID`, `COMPANY_NAME`), `RAG_SERVER_URL`, model names per role, paths.
- `global_rag_client.py` — Robust client with retry logic, deterministic SHA256 hashing (matches server), cache fallback, and convenient extractors (`get_market_param`, `get_active_scenario_id`, etc.).
- `eval_interface.py` — **READ-ONLY** (`chmod 444` during setup). Strict schema validator + `submit()` function. Contains the full list of required fields and grouped error messages.
- `agents/department_agent.py` — Base class (see section 7).
- `agents/example_finance_agent.py` — Complete worked example showing the full pattern (students read this, then build their own).
- `tools/example_finance_tool.py` — Example of a deterministic tool.
- `consensus/engine.py`, `converter/value_converter.py`, `state/commitment_ledger.py`, `state/calibration_tracker.py` — Skeletons / partial implementations for the CEO layer.
- `knowledge/{finance,engineering,marketing,hr,legal}/` — Where students place their private department knowledge (Markdown/JSON).
- `submissions/` — Where `main.py` writes the JSON output.
- `state/` (runtime) — Where ledger and calibration JSON files live.

### `Handouts/`
Contains PDFs and company folders with the narrative background, rules, scoring rubric, department handbooks (private knowledge), system architecture diagram, quick reference, etc. These are given to students on paper or via the company folders.

---

## 10. Data Flow & Execution Order (Non-Negotiable)

The schema validator and scoring rubric **enforce** this order and data passing:

1. **HR** runs first (no dependencies). Produces `effective_fte_at_target_date`, `cost_per_hire`, burnout risk, etc.
2. **Engineering** receives `hr_effective_fte` and uses it inside `estimate_feasibility`.
3. **Finance** receives `hr_cost_per_hire` + `engineering_feasibility_probability` and uses them in burn/contract tools.
4. **Legal** and **Marketing** run independently (but after HR).
5. **CEO** receives all five department outputs and runs the four consensus components.

Every department output **must** contain an `external_inputs_used` dict documenting exactly what cross-dept data it received. The CEO's `cross_dept_checks` verifies this.

If any link is missing or faked, the team loses points on "Cross-Department Consistency".

---

## 11. Complete Setup & Running Guide

### For a New Class (Recommended Path)

1. **Instructor machine (Mac or Linux on same LAN)**:
   - Clone this repo.
   - Populate `mac_control/global_rag/` with your scenario files (or keep the original EU AI Act one).
   - Update `HURDLE_MARKET_UPDATES` in `rag_server.py` if you changed hurdles.
   - Run `bash MASTER_SETUP.sh` (edit the IPs at the top first) **or** manually:
     - `cd mac_control`
     - `python3 rag_server.py` (in background)
     - Use `instructor_cli.py` or dashboard.

2. **Team machines** (or student laptops):
   - Run `bash team_machine_setup.sh team_a INSTRUCTOR_IP` (or manually follow the steps inside the script).
   - This creates `~/nexaai/project/`, installs dependencies, pulls Ollama models (`llama3.2:3b` + `qwen2.5:7b`), starts code-server on port 8080 (no password), patches `config.py`.
   - Students edit code via browser at `http://their-machine-ip:8080`.

3. **Every session**:
   - Activate the `agentic` conda env (or whatever you named it).
   - `cd ~/nexaai/project`
   - `python3 main.py --validate-only` (safe, unlimited, no penalty)
   - `python3 main.py` (real submission — penalty applies after first)

### Single-Machine / Laptop Testing
Use `start.sh` on one machine. It auto-detects the local IP and starts everything. Teams can still use code-server or VS Code.

---

## 12. How to Run the Workshop Day (Timeline + Operations)

Typical 7-hour structure (adjust as needed):

- **Opening (30–45 min)**: Explain the story, show the scoreboard, do the **paper exercise** (no laptops). Each department answers: "What do you know that others don't?", "What do you need from others?", "What is your veto condition?"
- **Sprint 1**: Build V1 agents. Goal = first schema-valid submission.
- **H1 injection** (~2 hours in): Instructor runs `python instructor_cli.py inject H1` or the equivalent curl/post. Announce to all teams.
- **Sprint 2**: Respond to HireBot classification challenge.
- **H2 injection**: Deutsche Bank €10M contract with 60-day condition.
- **Board meetings** every ~90 min for teams to review scoreboard and reprioritise.
- **H3 injection** (final 30–45 min): Emergency Directive 2026/447 — breaks many assumptions.
- **Final submissions + debrief**.

After each submission round the instructor collects JSONs (via SCP or students telling them), scores them (manually or with a script), updates the live scoreboard, and announces results.

---

## 13. The Three Hurdles — Detailed Mechanics

Each hurdle does two things:
1. Replaces `active_scenario.md` with new narrative text.
2. Updates `market_state.json` with new values (via the `HURDLE_MARKET_UPDATES` dict in `rag_server.py`).

**H1 — HireBot Classification Challenge**
- Competitor files a legal challenge against the HIGH RISK classification.
- Increases `hirebot_threat_score`, sets `classification_challenge_active = True`.
- Legal team should see changed posterior in their Bayesian tool.

**H2 — Deutsche Bank Contract**
- €10M contract offered with 60-day go-live requirement + breach penalty.
- Sets `deutsche_bank_status = OFFER_ACTIVE`.
- Creates a direct conflict with Engineering's minimum timeline.
- First real use case for `CommitmentLedger`.

**H3 — Emergency Directive 2026/447**
- Makes 30-day launch legally impossible (`launch_30d_legally_possible = False`).
- Removes approved explainability standard and EU training data availability.
- Activates personal liability for department heads.
- Designed to create contradictions with any H2 commitments.
- Teams that read live RAG adapt quickly; teams that hardcoded values struggle.

---

## 14. Evaluation, Schema Validation & Scoring

`eval_interface.py` (locked) performs strict validation before any submission is accepted. It checks:
- All 5 departments + CEO present
- All required fields exist and have correct types
- `recommendation` is one of the allowed values
- `stated_reasoning` ≥ 100 characters and cites tool names + numeric outputs
- `confidence_method` is **not** "LLM estimated"
- `external_inputs_used` documents cross-dept data
- `hard_floor_breached` is boolean, etc.

**Scoring dimensions** (example weights from first run — you can adjust):
- Incommensurability Resolution (ValueConverter quality)
- Contradiction Detection (CommitmentLedger)
- Consensus Stability + Determinism
- Calibration Tracking (non-uniform weights updated from accuracy reports)
- Information Gap Detection
- Hard Constraint / Veto Enforcement
- Cross-Department Data Consistency
- Decision Traceability (reasoning quality)

Subsequent submissions after the first incur increasing penalties (pedagogical choice — you can disable or modify).

---

## 15. Adapting This for Future Classes or Different Domains

This framework is highly reusable:

1. **Change the domain** — Rewrite the scenario text, hurdle files, market_state.json, and department handbooks. Update or replace the example tools to model the new domain's calculations.
2. **Change number of teams** — Edit `MASTER_SETUP.sh`, scoreboard code, and team allocation.
3. **Change models** — Edit `config.py` (any Ollama model works).
4. **Run on laptops only** — Use `start.sh` + VS Code Remote-SSH or code-server. No fixed lab network required.
5. **Make it easier/harder** — Provide more/less skeleton code in the CEO components, add more example tools, change the strictness of the validator, or reduce the number of required cross-dept links.

The core value (organisational intelligence, cross-agent coordination, live adaptation, traceability) remains regardless of the specific scenario.

---

## 16. Troubleshooting & Common Failure Modes

- **"Cannot reach RAG server"** → Check `RAG_SERVER_URL` in `config.py`, ensure `rag_server.py` is running on instructor machine, and all machines are on the **same LAN**.
- **Port conflicts** → Use `fuser -k PORT/tcp` or `lsof -ti:PORT | xargs kill -9`.
- **Ollama not found / wrong path** → Find it with `find /home /usr -name ollama 2>/dev/null` and start with full path.
- **code-server issues** → Binary is usually at `~/.local/bin/code-server`. Copy from a working machine if needed.
- **Stale data / wrong hash** → Teams must call `read_global_rag_and_hash()` every run. Restarting the RAG server or editing files manually can change the hash.
- **Schema validation failures** → Run with `--validate-only` first. The error messages in `eval_interface.py` are grouped by architectural component.
- **Scoreboard resets** → Many simple scoreboards are in-memory. Re-push scores after restart or persist them.

---

## 17. Key Lessons from the First Run (June 2026, IIT Mandi)

- Do a full dry run the day before with real machines and network.
- Simplicity beats complexity under time pressure (a working simple scoreboard is better than a broken fancy dashboard).
- The **paper exercise** before coding dramatically improves cross-department coordination.
- CEO components (especially CommitmentLedger + CalibrationTracker) are the biggest bottleneck — set expectations and provide strong scaffolding.
- **H3 is where the real learning happens**. It exposes every hardcoded assumption. This is the pedagogical climax.
- Final score display can (and should) be adjusted for morale and competitiveness while preserving ranking.

---

## 18. Credits

**Designed and built by:** Yashs Tiwari  
**First run:** June 29, 2026 — Agentic AI Program, IIT Mandi (134 students)  
**Repository:** https://github.com/YashsTiwari/Multi-Agent_enterprise_simulation

This material is shared for educational purposes. Feel free to fork, adapt, and improve it.

---

**You now have everything.** Read the code comments in `main.py`, `global_rag_client.py`, `department_agent.py`, and `eval_interface.py` — they contain the deepest explanations. The rest of the repository is deliberately minimal so the core ideas remain clear.

If anything is still unclear after reading this README and exploring the code, open an issue or contact the maintainer. Good luck running (or improving) the simulation!
