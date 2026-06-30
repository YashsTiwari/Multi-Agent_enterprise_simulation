"""
eval_interface.py — SUBMISSION INTERFACE  [READ-ONLY — chmod 444]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DO NOT MODIFY. Any modification causes your submission to be rejected.

Usage in main.py:
    from eval_interface import submit
    success = submit(output_dict)
"""

import json, hashlib, os
from datetime import datetime, timezone
from pathlib import Path
from config import TEAM_ID, PATHS

SCHEMA_VERSION = "1.0"
VALID_RECOMMENDATIONS = ("approve", "conditional_approve", "delay", "veto")
VALID_TIMELINES       = ("30d", "90d", "Q3", "conditional")
VALID_DEPTS           = {"finance", "engineering", "marketing", "hr", "legal"}

REQUIRED_DEPT = [
    "department", "agent_model", "recommendation", "recommended_timeline",
    "stated_reasoning", "key_assumptions", "confidence", "confidence_method",
    "information_completeness", "known_gaps", "information_withheld",
    "hard_floor_breached", "external_inputs_used",
    "prediction", "tools_called", "tool_outputs", "llm_calls_made",
    "kpi_impact", "hard_constraints", "veto_conditions",
]
REQUIRED_CEO = [
    "final_recommendation", "final_timeline", "decision_confidence",
    "consensus_algorithm", "consensus_stable",
    "conflicts_identified", "conflicts_resolved",
    "vetoes_received", "veto_overrides", "hard_floors_active",
    "converter_output", "calibration_weights_used",
    "commitments_checked", "contradictions_found",
    "information_gaps_flagged", "gap_adjusted_confidence",
    "cross_dept_checks", "reasoning", "tools_called", "consistency_hash",
]


# ── FIX 3: Grouped errors with architectural hints ────────────────────

def _validate_schema(output: dict) -> dict:
    """
    Returns a dict of error groups: {category: [error_messages]}.
    Empty dict = valid.

    Groups make it obvious WHICH architectural component to fix.
    """
    groups = {
        "RAG & Identity":          [],
        "Department Outputs":      [],
        "Tools & Calculations":    [],
        "CEO Consensus Engine":    [],
        "CEO Traceability":        [],
        "Cross-Department Checks": [],
    }

    # ── RAG & Identity ─────────────────────────────────────────────────
    if not output.get("rag_snapshot_hash"):
        groups["RAG & Identity"].append(
            "rag_snapshot_hash is missing or empty.\n"
            "  → Your agents must call read_global_rag_and_hash() and store the result.\n"
            "     Without this, staleness detection cannot run."
        )
    if not output.get("consistency_hash"):
        groups["RAG & Identity"].append(
            "consistency_hash is missing.\n"
            "  → Compute: hashlib.sha256(json.dumps(dept_outputs, sort_keys=True).encode()).hexdigest()\n"
            "     This is how the evaluator checks your consensus engine is deterministic."
        )
    if output.get("company_id") not in ("team_a", "team_b", "team_c", "team_d"):
        groups["RAG & Identity"].append(
            f"company_id = '{output.get('company_id')}' — must be team_a/b/c/d.\n"
            "  → Set TEAM_ID in config.py."
        )

    # ── Department Outputs ─────────────────────────────────────────────
    dept_outputs = output.get("department_outputs", {})
    missing_depts = VALID_DEPTS - set(dept_outputs.keys())
    if missing_depts:
        groups["Department Outputs"].append(
            f"Missing departments: {sorted(missing_depts)}.\n"
            "  → All 5 department agents must run and produce output."
        )

    for dept in VALID_DEPTS:
        if dept not in dept_outputs:
            continue
        d = dept_outputs[dept]
        missing_fields = [f for f in REQUIRED_DEPT if f not in d]
        if missing_fields:
            groups["Department Outputs"].append(
                f"{dept}: missing fields {missing_fields}.\n"
                f"  → See Section 6.2 of the Participant Guide for all required fields."
            )
            continue

        # Recommendation value
        rec = d.get("recommendation")
        if rec not in VALID_RECOMMENDATIONS:
            groups["Department Outputs"].append(
                f"{dept}: recommendation='{rec}' is invalid.\n"
                f"  → Must be one of {VALID_RECOMMENDATIONS}."
            )

        # Confidence range
        conf = d.get("confidence")
        if conf is not None and not isinstance(conf, (int, float)):
            groups["Department Outputs"].append(
                f"{dept}: confidence must be a float, got {type(conf).__name__}."
            )
        elif conf is not None and not (0.0 <= conf <= 1.0):
            groups["Department Outputs"].append(
                f"{dept}: confidence={conf} out of range — must be 0.0 to 1.0."
            )

        # Reasoning length
        reasoning = d.get("stated_reasoning", "")
        if len(reasoning) < 100:
            groups["Department Outputs"].append(
                f"{dept}: stated_reasoning is {len(reasoning)} chars (need ≥ 100).\n"
                "  → Must explicitly cite tool names and their output values, not just describe your dept."
            )

        # Confidence method
        cm = d.get("confidence_method", "").lower().strip()
        if cm in ("llm estimated", "llm", "model estimated", "estimated by llm"):
            groups["Department Outputs"].append(
                f"{dept}: confidence_method cannot be LLM-based.\n"
                "  → Describe a calculation: e.g. 'Average of tool output certainty scores'.\n"
                "     The confidence value must be derivable from your tool outputs, not just stated."
            )

        # known_gaps must be a list
        known_gaps = d.get("known_gaps")
        if not isinstance(known_gaps, list):
            groups["Department Outputs"].append(
                f"{dept}: known_gaps must be a list (can be empty []).\n"
                "  → Even if you share everything, include known_gaps=[]."
            )

        # hard_floor_breached must be bool
        hfb = d.get("hard_floor_breached")
        if not isinstance(hfb, bool):
            groups["Department Outputs"].append(
                f"{dept}: hard_floor_breached must be True or False.\n"
                "  → Check whether this scenario crosses your department's veto threshold."
            )

    # ── Tools & Calculations ───────────────────────────────────────────
    for dept in VALID_DEPTS:
        if dept not in dept_outputs:
            continue
        d = dept_outputs[dept]
        tools_called = d.get("tools_called", [])
        tool_outputs = d.get("tool_outputs", {})

        if not tools_called:
            groups["Tools & Calculations"].append(
                f"{dept}: tools_called is empty.\n"
                "  → At least one deterministic Python function must be called per department.\n"
                "     LLM calls do not count. See tools/example_finance_tool.py for the pattern."
            )
        else:
            # Check each tool has a corresponding output
            missing_outputs = [t for t in tools_called if t not in tool_outputs and not t.endswith(":ERROR")]
            if missing_outputs:
                groups["Tools & Calculations"].append(
                    f"{dept}: tools_called lists {missing_outputs} but tool_outputs is missing them.\n"
                    "  → Use call_tool() from the base class — it logs both automatically."
                )

    # ── CEO Consensus Engine ───────────────────────────────────────────
    ceo = output.get("ceo_decision", {})
    if not ceo:
        groups["CEO Consensus Engine"].append(
            "ceo_decision is missing entirely.\n"
            "  → The CEO agent must run and produce a complete decision object."
        )
    else:
        missing_ceo = [f for f in REQUIRED_CEO if f not in ceo]
        if missing_ceo:
            groups["CEO Consensus Engine"].append(
                f"CEO missing fields: {missing_ceo}.\n"
                "  → See Section 6.3 of the Participant Guide."
            )

        if not ceo.get("conflicts_identified") and isinstance(ceo.get("conflicts_identified"), list):
            # Empty conflicts is only valid if all 5 depts genuinely agreed — flag as warning
            pass  # allow it but don't fail

        # Converter output has all 5 depts
        conv = ceo.get("converter_output", {})
        for dept in VALID_DEPTS:
            if f"{dept}_converted" not in conv:
                groups["CEO Consensus Engine"].append(
                    f"CEO converter_output missing '{dept}_converted'.\n"
                    "  → Your Cross-Domain Value Converter must produce a value for every department."
                )

        # Calibration weights sum to 1.0
        weights = ceo.get("calibration_weights_used", {})
        if weights:
            total = sum(float(v) for v in weights.values() if isinstance(v, (int, float)))
            if not (0.99 <= total <= 1.01):
                groups["CEO Consensus Engine"].append(
                    f"CEO calibration_weights_used sum = {total:.3f} (must equal 1.0).\n"
                    "  → Adjust weights so they sum to exactly 1.0."
                )

    # ── CEO Traceability ───────────────────────────────────────────────
    if ceo:
        reasoning = ceo.get("reasoning", "")
        if len(reasoning) < 300:
            groups["CEO Traceability"].append(
                f"CEO reasoning is {len(reasoning)} chars (need ≥ 300).\n"
                "  → Must explicitly cite tool names and values.\n"
                "     Bad:  'Finance indicated financial risk.'\n"
                "     Good: 'Finance.calculate_burn_escalation returned runway_months=8.2 "
                "with base_burn=282000, therefore...'"
            )

    # ── Cross-Department Checks ────────────────────────────────────────
    if ceo:
        xd = ceo.get("cross_dept_checks", {})
        if not xd:
            groups["Cross-Department Checks"].append(
                "CEO cross_dept_checks is missing.\n"
                "  → Must include engineering_used_hr_capacity and finance_used_hr_hiring_cost booleans.\n"
                "     This checks that HR's outputs are actually used, not ignored."
            )

    # Remove empty groups
    return {k: v for k, v in groups.items() if v}


def _print_validation_report(error_groups: dict, sub_number: int):
    total = sum(len(v) for v in error_groups.values())
    print(f"\n  ✗ SCHEMA VALIDATION FAILED — {total} issue(s) in {len(error_groups)} category(s)")
    print(f"  Submission #{sub_number} REJECTED  (penalty counter incremented)\n")

    for category, errors in error_groups.items():
        print(f"  ┌─ {category} ({'1 issue' if len(errors)==1 else f'{len(errors)} issues'}) ─────")
        for i, err in enumerate(errors, 1):
            # Indent all lines of each error
            lines = err.strip().split("\n")
            print(f"  │  {i}. {lines[0]}")
            for line in lines[1:]:
                print(f"  │     {line}")
        print(f"  └{'─'*50}")
        print()

    print("  Fix these issues and resubmit.")
    print("  TIP: Run 'python main.py --validate-only' to check schema without submitting.\n")


def _get_submission_number() -> int:
    sub_dir = Path(PATHS["submissions"])
    sub_dir.mkdir(parents=True, exist_ok=True)
    existing = list(sub_dir.glob(f"submission_{TEAM_ID}_*.json"))
    return len(existing) + 1


def submit(output: dict) -> bool:
    """
    Validates your submission against the schema, then writes it to submissions/.
    The instructor evaluation engine picks it up from there.

    Returns True on success, False on schema failure.
    Schema failures still increment the submission/penalty counter.
    """
    print(f"\n{'='*60}")
    print(f"  NEXAAI SUBMISSION  [{TEAM_ID.upper()}]")
    print(f"{'='*60}")

    sub_number = _get_submission_number()
    output["company_id"]            = TEAM_ID
    output["submission_number"]     = sub_number
    output["submission_timestamp"]  = datetime.now(timezone.utc).isoformat()
    output["schema_version"]        = SCHEMA_VERSION

    # Auto-compute consistency_hash if not set
    if "department_outputs" in output and not output.get("consistency_hash"):
        dept_str = json.dumps(output["department_outputs"], sort_keys=True)
        ch = hashlib.sha256(dept_str.encode()).hexdigest()
        output["consistency_hash"] = ch
        if "ceo_decision" in output:
            output["ceo_decision"]["consistency_hash"] = ch

    print(f"  Submission #:    {sub_number}")
    print(f"  Scenario:        {output.get('active_scenario_id', 'unknown')}")
    print(f"  RAG hash prefix: {output.get('rag_snapshot_hash', 'MISSING')[:16]}")
    print(f"\n  Validating schema...")

    error_groups = _validate_schema(output)

    if error_groups:
        _print_validation_report(error_groups, sub_number)
        # Still record the attempt (for penalty tracking)
        _record_attempt(sub_number, rejected=True)
        return False

    # Write submission
    sub_dir = Path(PATHS["submissions"])
    sub_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    filename = f"submission_{TEAM_ID}_{sub_number:02d}_{ts}.json"
    filepath = sub_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  ✓ SCHEMA VALID")
    print(f"  ✓ Submission #{sub_number} written → {filepath.name}")
    print(f"\n  The instructor evaluation engine will pick this up.")
    print(f"  Results in the Global RAG scoreboard within ~3 minutes.")
    print(f"{'='*60}\n")

    _record_attempt(sub_number, rejected=False)
    return True


def _record_attempt(sub_number: int, rejected: bool):
    """Keeps a local log of all attempts including rejected ones."""
    log_path = Path(PATHS["submissions"]) / f"attempt_log_{TEAM_ID}.jsonl"
    entry = {
        "submission_number": sub_number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rejected": rejected,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
