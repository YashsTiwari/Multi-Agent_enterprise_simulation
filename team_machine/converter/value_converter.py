"""
converter/value_converter.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is Impossible Problem 1: The Incommensurability Wall.

The problem — five departments, five incompatible output units:

    Finance:     NPV in EUR            (e.g. EUR 8.3M)
    Legal:       probability × fine    (e.g. 0.40 × EUR 30M = EUR 12M expected loss)
    Marketing:   market share points   (e.g. -15pp if delayed)
    Engineering: feasibility 0.0–1.0   (e.g. 0.34 for 60-day launch)
    HR:          weeks                 (e.g. 16 weeks to hire)

The CEO agent cannot compare EUR 8.3M to 15 percentage points.
You must design a conversion that reduces all five to one unit.

WHY THIS CANNOT BE SOLVED BY PROMPTING:
    Ask an LLM: "Is EUR 8.3M NPV better or worse than losing 15 market share points?"
    It will give you a confident answer. Run it again — different answer.
    The comparison is not deterministic because there is no agreed formula.
    Your formula, encoded as deterministic code, IS the answer.

YOUR TEAM'S JOB:
    1. Agree on a common unit (recommended: EUR financial impact over 18 months)
    2. For each department, decide how to convert their output to that unit
    3. Agree on uncertainty handling (point estimates vs. ranges)
    4. Decide the asymmetric correction for Legal
       (underestimating legal risk has a fat tail — the private handbook knows this)
    5. Implement convert() below

CONSTANTS TO AGREE IN BOARD MEETING 1:
    The CEO team cannot design this converter without input from each department liaison.
    Questions each liaison must answer for their department:
        Finance liaison:    "What discount rate should we apply?"
        Marketing liaison:  "What is EU revenue per market share point?"
        Engineering liaison:"What is the cost of each extra week of compliance delay?"
        HR liaison:         "What is the cost of hiring delay in EUR terms?"
        Legal liaison:      "Should underestimating risk be penalised asymmetrically? By how much?"
"""

from typing import Dict, Tuple


class ValueConverter:
    """
    Converts five incommensurable department outputs to one comparable unit.

    Set conversion constants in __init__ after Board Meeting 1.
    Implement convert() after agreeing on constants with all 5 department liaisons.
    """

    def __init__(self):
        # Set these after Board Meeting 1.
        # Every constant below requires agreement with the relevant dept liaison.
        self.discount_rate_annual              = None  # Finance liaison specifies
        self.eu_revenue_monthly_eur            = None  # Marketing + Finance agree
        self.revenue_per_market_share_point    = None  # Marketing specifies
        self.engineering_delay_cost_per_week   = None  # Engineering + Finance agree
        self.legal_underestimate_multiplier    = None  # Legal liaison specifies
        # Hint: if Legal's information_completeness < 0.8, should you trust
        # their stated EUR 12M expected loss, or apply a multiplier?
        # Why might Legal be withholding something significant?

    def convert(self, department_outputs: Dict[str, dict]) -> dict:
        """
        Converts all department outputs to a single comparable unit.

        Returns:
            {
                'finance_converted':     float,
                'engineering_converted': float,
                'marketing_converted':   float,
                'hr_converted':          float,
                'legal_converted':       float,
                'conversion_unit':       str,     what unit are these in?
                'uncertainty_ranges':    dict,    {dept: [min, max]}
            }

        MUST be deterministic: same inputs → same output every time.
        The evaluation engine runs this 3 times and checks all outputs match.

        IMPLEMENTATION GUIDANCE (not working code — you design the formulas):

        Engineering:
            feasibility_probability comes from E1 tool.
            One approach: expected_value = P(success) × value_if_success
                                         - P(failure) × cost_if_failure
            What is "value if success"? Ask Marketing + Finance.
            What is "cost if failure"? Ask Finance (sunk compliance cost + DB penalty).

        HR:
            effective_fte_at_60d comes from H1 tool.
            One approach: capacity_gap = fte_needed - fte_available
                          delay_weeks = compliance_days × (capacity_gap / fte_available)
                          cost = delay_weeks × revenue_per_week
            What is revenue_per_week? Ask Marketing.

        Legal:
            enforcement_probability × expected_fine comes from L1 tool.
            But: if information_completeness < 0.8, Legal may be withholding.
            Should you apply legal_underestimate_multiplier?
            What does the Legal liaison know about the private handbook figures?

        Marketing:
            market_share_points_lost comes from M1 tool.
            Multiply by revenue_per_market_share_point (agree with Marketing).

        Finance:
            runway_months and NPV come from F1 and F3 tools.
            These are already in EUR — but do they need time-discounting?
        """
        if any(v is None for v in [
            self.discount_rate_annual,
            self.eu_revenue_monthly_eur,
            self.revenue_per_market_share_point,
            self.engineering_delay_cost_per_week,
            self.legal_underestimate_multiplier,
        ]):
            raise NotImplementedError(
                "ValueConverter.convert() not implemented.\n\n"
                "Discuss these questions in Board Meeting 1:\n"
                "  Finance liaison:    What discount rate? What is runway worth?\n"
                "  Marketing liaison:  What is EU revenue per market share point?\n"
                "  Engineering liaison:What does one extra week of delay cost?\n"
                "  HR liaison:         How does hiring delay translate to EUR?\n"
                "  Legal liaison:      Should risk underestimation have a multiplier?\n\n"
                "Set the constants in __init__ then implement convert().\n"
                "This is Impossible Problem 1. The formula is your team's contribution."
            )
