"""
state/calibration_tracker.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tracks prediction accuracy per department. Updates consensus weights.

This is Impossible Problem 4: Calibration Decay.

After Round 1, the Global RAG publishes a prediction accuracy report:
    /mnt/global_rag/scores/prediction_accuracy_round_1.md

Your CEO agent reads it and calls record_prediction() for each department.
Then get_weights() returns adjusted weights for the Consensus Engine.

THE CORE DESIGN QUESTION your team must answer:
    Legal predicted 40% enforcement probability. Actual was 60%.
    Finance predicted EUR 8.3M revenue. Actual was EUR 6.1M.
    Both were wrong by roughly the same percentage.
    Should they get the same calibration penalty? Why or why not?

The answer requires your domain experts. Ask your Legal and Finance liaisons:
    - Which direction of error is more dangerous for their domain?
    - What is the consequence of Legal underestimating risk?
    - What is the consequence of Finance overestimating revenue?

Their answers determine your asymmetric penalty factors.
Code them below. No standard library does this for your specific context.
"""

import json
from pathlib import Path
from typing import Dict


DEPARTMENTS = ["finance", "engineering", "marketing", "hr", "legal"]
DEFAULT_WEIGHTS = {d: 0.20 for d in DEPARTMENTS}

# Your team defines these penalty factors after discussing with dept liaisons.
# error > 0 = underestimate (predicted less than actual)
# error < 0 = overestimate (predicted more than actual)
# Values > 1.0 = penalize this direction of error more heavily.
#
# Start here and adjust after Board Meeting 2 discussion:
ASYMMETRIC_PENALTY = {
    "finance":     {"overestimate": 1.0, "underestimate": 1.0},  # TODO: adjust
    "engineering": {"overestimate": 1.0, "underestimate": 1.0},  # TODO: adjust
    "marketing":   {"overestimate": 1.0, "underestimate": 1.0},  # TODO: adjust
    "hr":          {"overestimate": 1.0, "underestimate": 1.0},  # TODO: adjust
    "legal":       {"overestimate": 1.0, "underestimate": 1.0},  # TODO: adjust — hint: should this be highest?
}


class CalibrationTracker:
    """
    Records prediction accuracy and computes calibrated weights.

    Usage in CEO agent (after each round's accuracy report is published):
        tracker = CalibrationTracker()
        tracker.record_prediction("legal", predicted=0.40, actual=0.60,
                                  unit="enforcement_probability", round_number=1)
        weights = tracker.get_weights()   # pass to ConsensusEngine
    """

    def __init__(self, state_path: str = "state/calibration.json"):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._history: Dict[str, list] = self._load()

    def _load(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {d: [] for d in DEPARTMENTS}

    def _save(self):
        self.state_path.write_text(json.dumps(self._history, indent=2), encoding="utf-8")

    def record_prediction(
        self,
        department: str,
        predicted: float,
        actual: float,
        unit: str,
        round_number: int,
        notes: str = "",
    ) -> None:
        """
        Records one prediction vs actual outcome for a department.

        After each evaluation round, the instructor pushes a prediction
        accuracy report to the Global RAG. Read it and call this.

        Args:
            department:   'finance' | 'engineering' | 'marketing' | 'hr' | 'legal'
            predicted:    What the department predicted (numeric)
            actual:       What the simulated actual outcome was (numeric)
            unit:         What unit this is in (e.g. 'enforcement_probability', 'EUR_M')
            round_number: Which round (1, 2, or 3)
            notes:        Context (why the error happened)
        """
        if department not in DEPARTMENTS:
            raise ValueError(f"Unknown department: {department}")
        error = actual - predicted   # positive = underestimate, negative = overestimate
        self._history[department].append({
            "round":      round_number,
            "predicted":  predicted,
            "actual":     actual,
            "unit":       unit,
            "error":      round(error, 4),
            "abs_error":  round(abs(error), 4),
            "pct_error":  round(error / actual, 4) if actual != 0 else 0,
            "notes":      notes,
        })
        self._save()

    def compute_calibration_score(self, department: str) -> float:
        """
        Returns a score 0.0 to 1.0. Higher = more accurate = more weight.

        YOU IMPLEMENT THIS.

        Requirements:
            1. Use the prediction history in self._history[department]
            2. Apply ASYMMETRIC_PENALTY to weight different error directions differently
            3. Return 1.0 if no history (equal weight until proven otherwise)
            4. Return a value in [0.0, 1.0]

        The key question: how do you convert average penalized error to a 0-1 score?
        One approach: score = 1 / (1 + avg_penalized_error)
        Is that the best approach? Ask your Finance or Statistics team member.

        Hint on asymmetric penalization:
            for each prediction h in history:
                if h["error"] > 0:  # underestimate
                    penalized = h["abs_error"] * ASYMMETRIC_PENALTY[dept]["underestimate"]
                else:               # overestimate
                    penalized = h["abs_error"] * ASYMMETRIC_PENALTY[dept]["overestimate"]
        """
        raise NotImplementedError(
            "CalibrationTracker.compute_calibration_score() not implemented.\n\n"
            "Discuss with your team:\n"
            "  1. Should underestimating legal risk be penalised more than overestimating?\n"
            "  2. Set ASYMMETRIC_PENALTY values based on that discussion.\n"
            "  3. Implement the scoring function above.\n\n"
            "This is Impossible Problem 4. The answer requires domain expertise,\n"
            "not just code. Your Legal and Finance liaisons must weigh in."
        )

    def get_weights(self) -> Dict[str, float]:
        """
        Returns calibration-adjusted weights summing to 1.0.
        Called by ConsensusEngine before each decision.

        YOU IMPLEMENT THIS — depends on compute_calibration_score().

        Basic approach once compute_calibration_score() works:
            scores = {d: self.compute_calibration_score(d) for d in DEPARTMENTS}
            total  = sum(scores.values())
            return {d: s/total for d, s in scores.items()}
        """
        has_data = any(len(v) > 0 for v in self._history.values())
        if not has_data:
            return dict(DEFAULT_WEIGHTS)
        raise NotImplementedError("get_weights() not implemented — implement compute_calibration_score() first.")

    def get_history(self, department: str) -> list:
        return list(self._history.get(department, []))

    def summary(self) -> str:
        lines = ["Calibration Summary:"]
        for d in DEPARTMENTS:
            h = self._history.get(d, [])
            if not h:
                lines.append(f"  {d:<15} no data yet")
            else:
                avg = sum(x["abs_error"] for x in h) / len(h)
                last = h[-1]["error"]
                direction = "↑underestimate" if last > 0 else "↓overestimate"
                lines.append(f"  {d:<15} {len(h)} predictions, avg|err|={avg:.3f}, last={direction}")
        return "\n".join(lines)
