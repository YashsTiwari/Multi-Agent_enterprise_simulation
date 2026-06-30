"""
state/commitment_ledger.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 5: CEO component skeleton — CommitmentLedger

The Commitment Ledger tracks decisions made in prior rounds.
When the scenario changes (new hurdle), it detects contradictions.

This file gives you the interface (method names + docstrings).
YOU implement the logic inside each method.

The CEO agent calls:
    ledger = CommitmentLedger()
    ledger.record(decision)           # after each CEO decision
    conflicts = ledger.check(scenario) # before each new decision
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class CommitmentLedger:
    """
    Tracks prior CEO decisions as binding commitments.
    
    Each commitment has:
      - decision:       what was decided (e.g. "accept_deutsche_bank_contract")
      - round_number:   which evaluation round this came from
      - reversibility:  float 0.0 (irreversible) to 1.0 (easily undone)
      - conditions:     what must be true for this commitment to hold
      - financial_cost: EUR amount spent/committed (negative = spent)
    
    The ledger persists to disk between rounds (state/commitments.json).
    This is HOW your CEO agent "remembers" prior decisions.
    """

    def __init__(self, state_path: str = "state/commitments.json"):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._commitments: list = self._load()

    def _load(self) -> list:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self):
        self.state_path.write_text(
            json.dumps(self._commitments, indent=2, default=str),
            encoding="utf-8"
        )

    def record(
        self,
        decision: str,
        round_number: int,
        reversibility: float,
        conditions: list,
        financial_cost: float = 0.0,
        notes: str = "",
    ) -> None:
        """
        Records a new commitment after a CEO decision.

        Args:
            decision:       Short label, e.g. "accepted_deutsche_bank_contract"
            round_number:   Current evaluation round (1, 2, 3...)
            reversibility:  0.0 = irreversible (money spent, contract signed)
                           1.0 = freely reversible (verbal indication only)
            conditions:     What must be true for this commitment to still hold.
                           e.g. ["eu_launch_within_60_days", "compliance_ready"]
            financial_cost: EUR impact. Negative = money spent.
            notes:          Free text for audit trail.

        Example:
            ledger.record(
                decision="accepted_deutsche_bank_contract",
                round_number=2,
                reversibility=0.2,  # contract can be renegotiated but not freely
                conditions=["eu_launch_within_60_days"],
                financial_cost=0,   # revenue on success, penalty on breach
                notes="EUR 10M contract, 60-day launch condition, EUR 500K breach penalty"
            )
        """
        # TODO: Implement this
        # Suggested: append to self._commitments, then call self._save()
        raise NotImplementedError(
            "CommitmentLedger.record() not implemented.\n"
            "Append a dict to self._commitments and call self._save()."
        )

    def check(self, new_scenario_text: str, market_state: dict) -> list:
        """
        Checks whether a new scenario contradicts existing commitments.

        Args:
            new_scenario_text:  Text of the current active scenario
            market_state:       Current market_state.json dict from RAG

        Returns:
            List of contradiction descriptions. Empty = no contradictions.

        Example contradictions to detect:
            - "accepted_deutsche_bank_contract" requires eu_launch_within_60_days
              but market_state["launch_90d_legally_possible"] == "UNCERTAIN"
              → contradiction: "DB contract requires 60-day launch but Directive 2026/447
                makes this timeline impossible"

        HINT:
            For each commitment, check whether its conditions are still met.
            Condition "eu_launch_within_60_days" means:
                engineering feasibility for 60d > 0.5
                AND legal compliance timeline ≤ 60 days
                AND market_state says launch is possible
        """
        # TODO: Implement this
        # Suggested approach:
        #   contradictions = []
        #   for commitment in self._commitments:
        #       for condition in commitment["conditions"]:
        #           if not self._condition_still_met(condition, market_state, new_scenario_text):
        #               contradictions.append(f"Commitment '{commitment['decision']}' "
        #                                     f"requires '{condition}' which is now violated")
        #   return contradictions
        raise NotImplementedError("CommitmentLedger.check() not implemented.")

    def get_all(self) -> list:
        """Returns all recorded commitments."""
        return list(self._commitments)

    def get_irreversible(self) -> list:
        """Returns commitments with reversibility < 0.3 (hard to undo)."""
        return [c for c in self._commitments if c.get("reversibility", 1.0) < 0.3]

    def total_financial_commitment(self) -> float:
        """Sums all financial costs (negative = money gone)."""
        return sum(c.get("financial_cost", 0.0) for c in self._commitments)
