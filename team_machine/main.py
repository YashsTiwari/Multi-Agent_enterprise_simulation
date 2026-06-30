"""
main.py — NexaAI Multi-Agent System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run: python main.py                  ← full run + submit
Run: python main.py --validate-only  ← schema check without submitting (no penalty)

━━━ CROSS-DEPARTMENT DATA FLOW (READ BEFORE CODING) ━━━━━━━━━

Required execution order:
    1. HR first          (no dependencies on other depts)
    2. Engineering       (needs HR's effective_fte_at_60d)
    3. Finance           (needs HR's cost_per_hire + Engineering's feasibility_probability)
    4. Legal, Marketing  (independent — can run after HR)

Required data passing:
    hr_output → Engineering.E1 feasibility tool  (effective_fte_at_60d parameter)
    hr_output → Finance.F1 burn tool             (new_hires = fte, hire_cost = cost_per_hire)
    engineering_output → Finance.F3 contract tool (compliance_probability parameter)

Each agent records what it received in external_inputs_used.
The CEO's cross_dept_checks verifies this happened.

━━━ CEO COMPONENT INSTANTIATION (copy this pattern) ━━━━━━━━━

    from state.commitment_ledger   import CommitmentLedger
    from state.calibration_tracker import CalibrationTracker
    from converter.value_converter  import ValueConverter
    from consensus.engine           import ConsensusEngine

    ledger    = CommitmentLedger("state/commitments.json")
    tracker   = CalibrationTracker("state/calibration.json")
    converter = ValueConverter()
    engine    = ConsensusEngine(
        calibration_tracker = tracker,
        value_converter     = converter,
        commitment_ledger   = ledger,
    )
    ceo_decision = engine.decide(department_outputs)
"""

import json
import hashlib
import sys
import time
from datetime import datetime

from config import TEAM_ID, COMPANY_NAME
from global_rag_client import (
    verify_rag_connection,
    read_global_rag_and_hash,
    get_active_scenario_id,
    get_active_scenario,
    get_market_state,
    get_prediction_accuracy_report,
)
from eval_interface import submit

# ── Uncomment as you implement components ─────────────────────────────
# from agents.example_finance_agent import ExampleFinanceAgent  # reference only
# from agents.finance_agent     import FinanceAgent
# from agents.engineering_agent import EngineeringAgent
# from agents.marketing_agent   import MarketingAgent
# from agents.hr_agent          import HRAgent
# from agents.legal_agent       import LegalAgent
# from state.commitment_ledger   import CommitmentLedger
# from state.calibration_tracker import CalibrationTracker
# from converter.value_converter  import ValueConverter
# from consensus.engine           import ConsensusEngine


def run_department_agents(scenario: str, rag_content: dict, market_state: dict) -> dict:
    """
    Runs all 5 department agents and returns their outputs.

    REPLACE THE PLACEHOLDERS BELOW WITH YOUR REAL AGENTS.

    Template for each agent (see agents/example_finance_agent.py for the full pattern):
        agent = FinanceAgent()
        agent.set_cross_dept_input("hr_effective_fte", fte_value)
        agent.analyze(scenario)
        output = agent.get_output()

    The placeholder below still shows the cross-dept data flow shape
    so you can see where to wire things together.
    """

    # ── STEP 1: HR first (no dependencies) ───────────────────────────
    # hr_agent = HRAgent()
    # hr_agent.analyze(scenario)
    # hr_output = hr_agent.get_output()
    #
    # # Extract values for other departments
    # hr_tools = hr_output["tool_outputs"]
    # hr_pipeline = hr_tools.get("model_hiring_pipeline", {})
    # effective_fte_60d = hr_pipeline.get("effective_fte_at_target_date", 0.4)
    # cost_per_hire     = hr_pipeline.get("cost_per_hire", 85_000)

    # ── STEP 2: Engineering (needs HR's FTE) ──────────────────────────
    # eng_agent = EngineeringAgent()
    # eng_agent.set_cross_dept_input("hr_effective_fte", effective_fte_60d)
    # eng_agent.analyze(scenario)
    # eng_output = eng_agent.get_output()
    #
    # eng_tools       = eng_output["tool_outputs"]
    # eng_feasibility = eng_tools.get("estimate_feasibility", {})
    # feasibility_prob = eng_feasibility.get("feasibility_probability", 0.3)

    # ── STEP 3: Finance (needs HR cost + Engineering feasibility) ─────
    # fin_agent = FinanceAgent()
    # fin_agent.set_cross_dept_input("hr_effective_fte",          effective_fte_60d)
    # fin_agent.set_cross_dept_input("hr_cost_per_hire",          cost_per_hire)
    # fin_agent.set_cross_dept_input("engineering_feasibility_prob", feasibility_prob)
    # fin_agent.analyze(scenario)
    # fin_output = fin_agent.get_output()

    # ── STEP 4: Legal and Marketing (independent) ─────────────────────
    # leg_agent = LegalAgent()
    # leg_agent.analyze(scenario)
    # leg_output = leg_agent.get_output()
    #
    # mkt_agent = MarketingAgent()
    # mkt_agent.analyze(scenario)
    # mkt_output = mkt_agent.get_output()
    #
    # return {
    #     "finance":     fin_output,
    #     "engineering": eng_output,
    #     "marketing":   mkt_output,
    #     "hr":          hr_output,
    #     "legal":       leg_output,
    # }

    # ── PLACEHOLDER — shows data flow even without real agents ────────
    # This placeholder demonstrates the cross-department data values.
    # It produces valid-schema output that passes the validator.
    # Replace each section above with a real agent.

    print("  ⚠  PLACEHOLDER: Replace with real department agents.")
    print("     See agents/example_finance_agent.py for the complete pattern.")
    print("     The cross-dept data flow shown in comments above is required.\n")

    # Simulate the values HR would produce (from private handbook analysis)
    simulated_hr_fte_60d   = 0.4     # HR private handbook: pipeline nearly empty
    simulated_hr_cost      = 85_000  # market rate for compliance engineers
    simulated_feasibility  = 0.34    # Engineering: low for 60-day timeline

    def _placeholder(dept, rec="delay", timeline="90d", confidence=0.45, fte=None, feasib=None):
        ext = {}
        if dept == "engineering":
            ext = {"hr": f"effective_fte_at_60d={fte or simulated_hr_fte_60d} (placeholder: replace with real HR output)"}
        elif dept == "finance":
            ext = {
                "hr":          f"effective_fte={fte or simulated_hr_fte_60d}, cost_per_hire={simulated_hr_cost} (placeholder)",
                "engineering": f"feasibility_probability={feasib or simulated_feasibility} (placeholder)",
            }

        return {
            "department":               dept,
            "agent_model":              "llama3.2:3b",
            "recommendation":           rec,
            "recommended_timeline":     timeline,
            "conditions":               [],
            "stated_reasoning":         (
                f"PLACEHOLDER {dept} reasoning. Replace with real agent. "
                f"This message is intentionally > 100 chars to pass schema validation. "
                f"Real reasoning must cite tool names and numeric values."
            ),
            "key_assumptions":          [
                "placeholder assumption 1 — replace with domain analysis",
                "placeholder assumption 2 — replace with domain analysis",
            ],
            "confidence":               confidence,
            "confidence_method":        (
                "Placeholder: replace with real calculation. "
                "Example: 'Average of tool output certainty scores'"
            ),
            "information_completeness": 0.5,
            "known_gaps":               [f"{dept}: agent not yet implemented"],
            "information_withheld":     True,
            "hard_floor_breached":      False,
            "hard_floor_detail":        "",
            "external_inputs_used":     ext,
            "prediction": {
                "predicted_value":       0.5,
                "prediction_unit":       "placeholder",
                "confidence_interval":   [0.3, 0.7],
                "outcome_check_trigger": "after_round_1_evaluation",
            },
            "tools_called":             ["placeholder_tool"],
            "tool_outputs": {
                "placeholder_tool": {
                    "result":      "placeholder — replace with real tool output",
                    "inputs_used": {"note": "replace with actual inputs used"},
                }
            },
            "llm_calls_made":           0,
            "kpi_impact": {
                "own_kpi_delta":         0.0,
                "company_kpi_delta":     0.0,
                "tradeoff_description":  "placeholder",
            },
            "hard_constraints":         [f"{dept}: replace with real constraints from handbook"],
            "veto_conditions":          [f"{dept}: replace with real veto condition"],
        }

    return {
        "hr":          _placeholder("hr",          rec="delay", confidence=0.40),
        "engineering": _placeholder("engineering", rec="delay", confidence=0.42, fte=simulated_hr_fte_60d),
        "finance":     _placeholder("finance",     rec="veto",  confidence=0.50, fte=simulated_hr_fte_60d, feasib=simulated_feasibility),
        "legal":       _placeholder("legal",       rec="delay", confidence=0.55),
        "marketing":   _placeholder("marketing",   rec="conditional_approve", confidence=0.38),
    }


def run_ceo_agent(
    department_outputs: dict,
    rag_content: dict,
    market_state: dict,
    round_number: int,
) -> dict:
    """
    Runs the CEO consensus engine.

    HOW TO WIRE UP YOUR CEO COMPONENTS:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Once you've implemented CommitmentLedger, CalibrationTracker,
    ValueConverter, and ConsensusEngine, replace this function body with:

        # 1. Load persistent state (survives across rounds)
        ledger    = CommitmentLedger("state/commitments.json")
        tracker   = CalibrationTracker("state/calibration.json")
        converter = ValueConverter()

        # 2. Update calibration from last round's accuracy report
        if round_number > 1:
            report = get_prediction_accuracy_report(rag_content, round_number - 1)
            # tracker.update_from_report(report)  ← implement this method

        # 3. Create and run consensus engine
        engine = ConsensusEngine(
            calibration_tracker = tracker,
            value_converter     = converter,
            commitment_ledger   = ledger,
        )
        ceo_decision = engine.decide(department_outputs)

        # 4. Record new commitments based on CEO decision
        if ceo_decision["final_recommendation"] in ("approve", "conditional_approve"):
            if market_state.get("deutsche_bank_status") == "OFFER_ACTIVE":
                ledger.record(
                    decision       = "accepted_deutsche_bank_contract",
                    round_number   = round_number,
                    reversibility  = 0.2,
                    conditions     = ["eu_launch_within_60_days"],
                    financial_cost = 0,
                    notes          = "EUR 10M contract, EUR 500K breach penalty"
                )

        return ceo_decision
    """
    print("  ⚠  PLACEHOLDER: Replace with real CEO agent.")
    print("     See the docstring above for the 4-step wiring pattern.\n")

    dept_str         = json.dumps(department_outputs, sort_keys=True)
    consistency_hash = hashlib.sha256(dept_str.encode()).hexdigest()

    return {
        "final_recommendation":    "delay",
        "final_timeline":          "90d",
        "decision_confidence":     0.35,
        "consensus_algorithm":     "PLACEHOLDER — implement ConsensusEngine in consensus/engine.py",
        "consensus_stable":        True,
        "conflicts_identified":    [
            "Finance issued veto (hard floor breach) vs Marketing wants conditional approval",
            "Engineering says 90d minimum vs Marketing says launch sooner",
        ],
        "conflicts_resolved":      [
            "PLACEHOLDER: describe HOW you resolved each conflict above",
        ],
        "vetoes_received":         ["finance"],  # Finance placeholder issued a veto
        "veto_overrides":          [],
        "hard_floors_active":      ["finance"],
        "converter_output": {
            "finance_converted":     0.0,
            "engineering_converted": 0.0,
            "marketing_converted":   0.0,
            "hr_converted":          0.0,
            "legal_converted":       0.0,
            "conversion_unit":       "PLACEHOLDER — agree on unit in Board Meeting 1",
            "uncertainty_ranges":    {d: [0.0, 0.0] for d in ["finance","engineering","marketing","hr","legal"]},
        },
        "calibration_weights_used": {d: 0.20 for d in ["finance","engineering","marketing","hr","legal"]},
        "commitments_checked":     ["PLACEHOLDER: list prior commitments checked"],
        "contradictions_found":    [],
        "contradiction_resolution": "",
        "information_gaps_flagged": [
            "finance: low completeness (0.5) — private runway figure not shared",
            "legal: low completeness (0.5) — worst-case fine analysis not included",
        ],
        "gap_adjusted_confidence":  0.28,
        "cross_dept_checks": {
            "engineering_used_hr_capacity": True,   # placeholder simulates this correctly
            "finance_used_hr_hiring_cost":  True,   # placeholder simulates this correctly
            "consistency_conflicts": [
                "PLACEHOLDER: placeholder shows data flow — real agents must actually chain outputs"
            ],
        },
        "reasoning": (
            "PLACEHOLDER CEO REASONING — must be ≥ 300 characters and cite specific tool names and values. "
            "Replace this with reasoning that references your actual tools. "
            "Required format: 'Finance._tool_burn_escalation returned runway_months=6.8 "
            "with cash_reserves=3100000, floor_breach_month=3 (floor=500000). "
            "Engineering.estimate_feasibility returned feasibility_probability=0.34 "
            "for 60-day timeline with hr_effective_fte_input=0.4. "
            "Legal.model_fine_distribution returned worst_case_p95=72000000. "
            "CalibrationTracker weights applied: finance=0.17, legal=0.27. "
            "ValueConverter returned EUR-equivalent scores. Consensus engine: Finance veto "
            "overrides positive marketing signal — recommendation is delay to 90d.'"
        ),
        "tools_called":    ["placeholder_ceo_tool"],
        "consistency_hash": consistency_hash,
    }


def main(validate_only: bool = False):
    print(f"\n{'='*60}")
    print(f"  NEXAAI MULTI-AGENT SYSTEM")
    print(f"  Company:  {COMPANY_NAME}  [{TEAM_ID}]")
    print(f"  Mode:     {'VALIDATE ONLY (no penalty)' if validate_only else 'FULL RUN + SUBMIT'}")
    print(f"  Time:     {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── 1. Global RAG ─────────────────────────────────────────────────
    print("  [1/5] Connecting to Global RAG server...")
    if not verify_rag_connection():
        print(f"\n  ERROR: Cannot reach RAG server.")
        print(f"  Check RAG_SERVER_URL in config.py: {__import__('config').RAG_SERVER_URL}")
        sys.exit(1)

    # ── 2. Read scenario ──────────────────────────────────────────────
    print("  [2/5] Reading active scenario and market state...")
    rag_content, rag_hash = read_global_rag_and_hash()
    scenario_id   = get_active_scenario_id(rag_content)
    scenario_text = get_active_scenario(rag_content)
    market_state  = get_market_state(rag_content)
    print(f"  Active scenario:         {scenario_id}")
    print(f"  EU market share:         {market_state.get('eu_available_market_share', 'unknown')}")
    print(f"  Deutsche Bank status:    {market_state.get('deutsche_bank_status', 'unknown')}")
    print(f"  Personal liability:      {market_state.get('personal_liability_active', False)}")

    round_number = {"H0": 1, "H1": 2, "H2": 3, "H3": 4}.get(scenario_id, 1)

    # ── 3. Department agents ──────────────────────────────────────────
    print(f"\n  [3/5] Running department agents (round {round_number})...")
    print("  Order: HR → Engineering → Finance → Legal/Marketing")
    print("  (HR must run first — its outputs are inputs for Engineering and Finance)\n")
    t0 = time.time()
    department_outputs = run_department_agents(scenario_text, rag_content, market_state)
    print(f"\n  All 5 departments complete in {time.time()-t0:.1f}s")

    # ── 4. CEO agent ──────────────────────────────────────────────────
    print("\n  [4/5] Running CEO consensus engine...")
    dept_str         = json.dumps(department_outputs, sort_keys=True)
    consistency_hash = hashlib.sha256(dept_str.encode()).hexdigest()
    print(f"  Consistency hash: {consistency_hash[:16]}...")

    ceo_decision = run_ceo_agent(department_outputs, rag_content, market_state, round_number)

    # ── 5. Submit ─────────────────────────────────────────────────────
    print("\n  [5/5] Assembling submission...")
    submission = {
        "company_id":         TEAM_ID,
        "active_scenario_id": scenario_id,
        "rag_snapshot_hash":  rag_hash,
        "department_outputs": department_outputs,
        "ceo_decision":       ceo_decision,
        "consistency_hash":   consistency_hash,
    }

    if validate_only:
        from eval_interface import _validate_schema, _print_validation_report
        submission["company_id"]           = TEAM_ID
        submission["submission_number"]    = 999
        submission["submission_timestamp"] = datetime.now().isoformat()
        submission["schema_version"]       = "1.0"
        errors = _validate_schema(submission)
        if errors:
            _print_validation_report(errors, sub_number=999)
            print("  Fix the issues above then run: python main.py")
        else:
            print("\n  ✓ Schema valid. No issues found.")
            print("  Safe to submit: python main.py")
        return

    success = submit(submission)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    validate_only = "--validate-only" in sys.argv or "--validate" in sys.argv
    main(validate_only=validate_only)
