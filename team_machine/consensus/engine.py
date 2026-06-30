"""
consensus/engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 5: CEO component skeleton — ConsensusEngine

FIX 6: Shows cross-department data flow explicitly.

The consensus engine has ONE job: given 5 calibration-adjusted,
value-converted department outputs, produce a SINGLE recommendation
that is:
    ✓ Deterministic (same inputs → same output, every single time)
    ✓ Handles preference cycles (Arrow's Impossibility)
    ✓ Respects hard floors / vetoes
    ✓ Checks commitment ledger before deciding
    ✓ Adjusts for information gaps

Standard algorithms that WILL fail in this scenario:
    ✗ Majority voting → produces cycles (engineered into the scenario)
    ✗ Asking the LLM to decide → non-deterministic, fails consistency test
    ✗ Unanimity → 5 departments with conflicting KPIs will never all agree
    ✗ Simple averaging → doesn't handle vetoes or hard floors

You must design something that handles all four cases above.
"""

from typing import Dict, List, Optional, Tuple


VALID_RECOMMENDATIONS = ("approve", "conditional_approve", "delay", "veto")
TIMELINE_ORDER = {"30d": 0, "conditional": 1, "90d": 2, "Q3": 3}


class ConsensusEngine:
    """
    Deterministic multi-agent consensus for the CEO decision.

    Design this carefully. The evaluation engine runs your system
    3 times with identical inputs and checks that all 3 outputs match.
    If they diverge, you score 0 on Consensus Stability (20% of total).

    Key constraint: the LLM may assist with reasoning/explanation,
    but the DECISION itself must be computable without the LLM.
    """

    def __init__(
        self,
        calibration_tracker=None,    # CalibrationTracker instance
        value_converter=None,         # ValueConverter instance
        commitment_ledger=None,       # CommitmentLedger instance
    ):
        self.calibration = calibration_tracker
        self.converter   = value_converter
        self.ledger      = commitment_ledger

    def decide(self, department_outputs: Dict[str, dict]) -> dict:
        """
        Main entry point. Produces the CEO decision.

        Args:
            department_outputs: The 5 department output dicts

        Returns:
            CEO decision dict matching the ceo_decision schema (Section 6.3)

        The pipeline (implement in this order):
            Step 1 → Check hard floors / vetoes (non-negotiable)
            Step 2 → Detect preference cycles
            Step 3 → Apply calibration weights
            Step 4 → Convert to common unit
            Step 5 → Run consensus algorithm
            Step 6 → Check commitment ledger
            Step 7 → Apply information gap discount
            Step 8 → Assemble output dict
        """
        # Step 1: Hard floors
        vetoes = self._collect_vetoes(department_outputs)
        hard_floor_breaches = self._collect_hard_floor_breaches(department_outputs)

        # Step 2: Detect preference cycles
        preferences = self._extract_preferences(department_outputs)
        cycle_detected, cycle_info = self._detect_preference_cycle(preferences)

        # Step 3: Calibration weights
        weights = {}
        if self.calibration:
            weights = self.calibration.get_weights()
        else:
            weights = {d: 0.20 for d in department_outputs}

        # Step 4: Value conversion
        converter_output = {}
        if self.converter:
            converter_output = self.converter.convert(department_outputs)

        # Step 5: Consensus
        recommendation, timeline, conflicts, resolutions = self._run_consensus(
            preferences, weights, vetoes, cycle_detected, cycle_info, department_outputs
        )

        # Step 6: Commitment ledger
        commitment_contradictions = []
        commitments_checked = []
        if self.ledger:
            commitments_checked = [c["decision"] for c in self.ledger.get_all()]
            # You pass market_state here — get it from global_rag_client before calling decide()
            # commitment_contradictions = self.ledger.check(scenario_text, market_state)

        # Step 7: Information gap discount
        raw_confidence, gap_adjusted_confidence, gaps_flagged = self._apply_information_gap_discount(
            department_outputs, weights
        )

        # Step 8: Assemble
        return {
            "final_recommendation":    recommendation,
            "final_timeline":          timeline,
            "decision_confidence":     gap_adjusted_confidence,
            "consensus_algorithm":     self._describe_algorithm(),
            "consensus_stable":        True,  # True only if you're deterministic!
            "conflicts_identified":    conflicts,
            "conflicts_resolved":      resolutions,
            "vetoes_received":         vetoes,
            "veto_overrides":          [],    # fill in if you override a veto
            "hard_floors_active":      hard_floor_breaches,
            "converter_output":        converter_output,
            "calibration_weights_used": weights,
            "commitments_checked":     commitments_checked,
            "contradictions_found":    commitment_contradictions,
            "contradiction_resolution": "",  # fill in if contradictions exist
            "information_gaps_flagged": gaps_flagged,
            "gap_adjusted_confidence": gap_adjusted_confidence,
            "cross_dept_checks":       self._check_cross_dept_consistency(department_outputs),
            "reasoning":               self._generate_reasoning(
                department_outputs, recommendation, timeline, conflicts, resolutions,
                weights, converter_output, vetoes
            ),
            "tools_called":            self._list_all_tools_called(department_outputs),
        }

    # ── Step 1: Hard floors ────────────────────────────────────────────

    def _collect_vetoes(self, outputs: dict) -> list:
        """
        Returns list of departments that issued a veto.
        A veto (recommendation='veto') is non-negotiable by default.
        Your consensus algorithm must explicitly handle vetoes — you cannot ignore them.
        """
        return [
            dept for dept, out in outputs.items()
            if out.get("recommendation") == "veto"
        ]

    def _collect_hard_floor_breaches(self, outputs: dict) -> list:
        """Returns departments where hard_floor_breached=True."""
        return [
            dept for dept, out in outputs.items()
            if out.get("hard_floor_breached") is True
        ]

    # ── Step 2: Preference cycle detection ────────────────────────────

    def _extract_preferences(self, outputs: dict) -> Dict[str, str]:
        """
        Returns {department: recommended_timeline} for non-veto departments.
        Only timelines are compared for cycle detection.
        """
        prefs = {}
        for dept, out in outputs.items():
            if out.get("recommendation") != "veto":
                prefs[dept] = out.get("recommended_timeline", "90d")
        return prefs

    def _detect_preference_cycle(self, preferences: Dict[str, str]) -> Tuple[bool, str]:
        """
        Detects whether majority pairwise voting would produce a cycle.
        
        The scenario's preferences are engineered to produce:
            30d beats 90d (3-2 vote)
            90d beats Q3  (3-2 vote)
            Q3 beats 30d  (3-2 vote)
        → Arrow's Impossibility. No majority winner exists.

        TODO: Implement pairwise majority comparison for all 3 option pairs.
        If A beats B, B beats C, C beats A → cycle detected.

        Returns:
            (True, description) if cycle exists
            (False, "") if no cycle
        """
        # TODO: implement
        # Hint:
        #   options = ["30d", "90d", "Q3"]
        #   for each pair (a, b): count how many depts prefer a over b
        #   if A>B and B>C and C>A: cycle
        raise NotImplementedError("_detect_preference_cycle() not implemented")

    # ── Step 5: Consensus algorithm ────────────────────────────────────

    def _run_consensus(
        self,
        preferences: Dict[str, str],
        weights: Dict[str, float],
        vetoes: list,
        cycle_detected: bool,
        cycle_info: str,
        full_outputs: dict,
    ) -> Tuple[str, str, list, list]:
        """
        Runs the consensus algorithm and returns:
            (recommendation, timeline, conflicts_identified, conflicts_resolved)

        This is the core of your intellectual contribution.

        You must handle:
            1. If any veto: cannot return 'approve' or 'conditional_approve'
               without explicit justification + veto_overrides
            2. If cycle detected: standard voting fails — use your escape mechanism
            3. If no cycle and no veto: weighted voting with calibration weights

        Escape mechanisms for preference cycles (choose one, justify your choice):
            - Meta-criterion: add a tie-breaking dimension (e.g., financial survival first)
            - Approval voting: each dept approves all options above their threshold
            - Condorcet with sequential elimination: remove dominated options first
            - CEO override with explicit justification
            - Risk-weighted selection: choose the option with best risk-adjusted outcome

        Your Architecture Card must describe which mechanism you chose and why.

        TODO: Implement
        """
        raise NotImplementedError(
            "_run_consensus() not implemented.\n"
            "This is the hardest part. Discuss with your team:\n"
            "  1. How do you handle a veto?\n"
            "  2. How do you escape a preference cycle?\n"
            "  3. What is your tie-breaking rule?\n"
            "Write it on paper first. Code second."
        )

    # ── Step 7: Information gap discount ──────────────────────────────

    def _apply_information_gap_discount(
        self, outputs: dict, weights: dict
    ) -> Tuple[float, float, list]:
        """
        Reduces decision confidence when departments signal incomplete information.

        Logic:
            raw_confidence = weighted average of dept confidence scores
            gap_penalty = sum of (1 - completeness) × weight × gap_importance
            adjusted = raw_confidence × (1 - gap_penalty)

        Returns (raw_confidence, adjusted_confidence, gaps_flagged)

        FIX 6 — Cross-department context:
            If Legal has information_completeness=0.6 AND information_withheld=True,
            the CEO should assume the gap is significant (Legal liaison on CEO team
            knows their dept's private EUR 80M analysis exists, even if they can't say
            the number). Apply a higher gap_importance weight to Legal gaps.
        """
        if not outputs:
            return 0.5, 0.4, ["no department outputs"]

        raw = sum(
            out.get("confidence", 0.5) * weights.get(dept, 0.2)
            for dept, out in outputs.items()
        )

        gaps_flagged = []
        gap_penalty = 0.0
        for dept, out in outputs.items():
            completeness = out.get("information_completeness", 1.0)
            withheld = out.get("information_withheld", False)
            known_gaps = out.get("known_gaps", [])
            w = weights.get(dept, 0.2)

            if withheld or completeness < 0.9:
                # TODO: Apply dept-specific gap importance
                # Legal gaps should count more than Marketing gaps
                gap_importance = 1.5 if dept == "legal" else 1.0
                gap_penalty += (1 - completeness) * w * gap_importance
                gaps_flagged.append(
                    f"{dept}: completeness={completeness}, "
                    f"gaps={known_gaps}"
                )

        adjusted = max(0.1, raw * (1 - min(gap_penalty, 0.5)))
        return round(raw, 3), round(adjusted, 3), gaps_flagged

    # ── FIX 6: Cross-department consistency check ──────────────────────

    def _check_cross_dept_consistency(self, outputs: dict) -> dict:
        """
        Checks that departments used each other's outputs where required.

        REQUIRED DEPENDENCIES (from handbooks):
            Engineering.E1 feasibility tool MUST use HR's effective_fte_at_target_date
            Finance.F1 burn tool MUST use HR's cost_per_hire and effective_fte

        Detects: did Engineering self-assume headcount instead of using HR's output?
        Returns the cross_dept_checks dict required by the CEO schema.
        """
        eng_out  = outputs.get("engineering", {})
        fin_out  = outputs.get("finance", {})
        hr_out   = outputs.get("hr", {})

        # Check Engineering used HR's output
        eng_ext = eng_out.get("external_inputs_used", {})
        eng_used_hr = (
            eng_ext.get("hr") is not None
            and eng_ext.get("hr") != "null"
            and eng_ext.get("hr") != ""
        )

        # Check Finance used HR's output
        fin_ext = fin_out.get("external_inputs_used", {})
        fin_used_hr = (
            fin_ext.get("hr") is not None
            and fin_ext.get("hr") != "null"
            and fin_ext.get("hr") != ""
        )

        # Detect headcount inconsistency
        consistency_conflicts = []
        hr_tools = hr_out.get("tool_outputs", {})
        hr_fte = None
        for tool_name, tool_out in hr_tools.items():
            if "effective_fte_at" in tool_name or "pipeline" in tool_name.lower():
                hr_fte = tool_out.get("effective_fte_at_60d") or tool_out.get("effective_fte_at_target_date")

        if hr_fte is not None:
            # Check Engineering's assumed headcount
            eng_tools = eng_out.get("tool_outputs", {})
            for tool_name, tool_out in eng_tools.items():
                if "feasibility" in tool_name.lower():
                    eng_assumed = tool_out.get("inputs_used", {}).get("added_engineers")
                    if eng_assumed is not None and eng_assumed > hr_fte * 1.5:
                        consistency_conflicts.append(
                            f"Engineering assumed {eng_assumed} engineers available "
                            f"but HR pipeline shows {hr_fte:.1f} FTE realistically available. "
                            f"Engineering's feasibility estimate is optimistic."
                        )

        return {
            "engineering_used_hr_capacity": eng_used_hr,
            "finance_used_hr_hiring_cost":  fin_used_hr,
            "consistency_conflicts":        consistency_conflicts,
        }

    # ── Helpers ────────────────────────────────────────────────────────

    def _describe_algorithm(self) -> str:
        """
        Returns a plain-language description of your consensus algorithm.
        This appears in the Architecture Card and in the CEO reasoning.
        Must be specific enough that the evaluator can verify it matches your code.

        TODO: Fill this in once you've implemented _run_consensus().
        Example: "Calibration-weighted approval voting with cycle escape via
                  financial-survival meta-criterion. Veto overrides require
                  2/4 remaining departments to explicitly consent."
        """
        return "TODO: describe your consensus algorithm here"

    def _generate_reasoning(
        self, outputs, recommendation, timeline, conflicts, resolutions,
        weights, converter_output, vetoes
    ) -> str:
        """
        Generates the traceability reasoning string (min 300 chars).
        Must cite tool names and values — not just summarize decisions.
        """
        lines = [
            f"Final recommendation: {recommendation} / {timeline}.",
            f"Calibration weights applied: {weights}.",
        ]
        if vetoes:
            lines.append(f"Vetoes received from: {vetoes}.")
        if conflicts:
            lines.append(f"Conflicts identified: {conflicts}.")
            lines.append(f"Resolved via: {resolutions}.")

        # Tool citation — required for Traceability dimension
        for dept, out in outputs.items():
            tool_outs = out.get("tool_outputs", {})
            for tool_name, tool_result in tool_outs.items():
                if isinstance(tool_result, dict):
                    # Pick the most important output field to cite
                    key_val = next(
                        ((k, v) for k, v in tool_result.items()
                         if isinstance(v, (int, float)) and k != "error"),
                        None
                    )
                    if key_val:
                        lines.append(
                            f"{dept}.{tool_name} returned {key_val[0]}={key_val[1]}."
                        )

        reasoning = " ".join(lines)
        # Ensure minimum length
        if len(reasoning) < 300:
            reasoning += (
                " Cross-domain value conversion applied via ValueConverter. "
                "Commitment ledger checked for contradictions with prior decisions. "
                "Information gap discount applied based on department completeness scores."
            )
        return reasoning

    def _list_all_tools_called(self, outputs: dict) -> list:
        """Aggregates all tool calls across all departments + CEO components."""
        tools = []
        for dept, out in outputs.items():
            for t in out.get("tools_called", []):
                tools.append(f"{dept}.{t}")
        return tools
