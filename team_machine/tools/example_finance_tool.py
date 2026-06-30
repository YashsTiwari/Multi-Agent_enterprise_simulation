"""
tools/example_finance_tool.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 4: One complete, correct tool implementation.

READ THIS BEFORE WRITING YOUR OWN TOOLS.

This file shows the PATTERN every department tool must follow:
  ✓ Takes specific numeric inputs (no LLM calls inside)
  ✓ Returns a dict with predictable keys
  ✓ Same inputs → same output every time (deterministic)
  ✓ Includes input validation
  ✓ Uses private knowledge from config, not hardcoded public figures

The Finance team must implement tools F1-F4 from the handbook.
This example shows a simplified version of F1 (Burn Escalation).
Use it as a reference — your real F1 tool is more complex.
"""

from dataclasses import dataclass
from typing import Optional


# ── The tool: a plain function, no LLM, no network calls ─────────────

def calculate_burn_escalation(
    base_burn_monthly: float,
    new_hires: int,
    hire_salary_annual: float,
    infra_spend_onetime: float,
    compliance_spend_monthly: float,
    months: int,
    cash_reserves: float,
    emergency_floor: float = 500_000,
) -> dict:
    """
    Calculates the true monthly burn rate and runway given new spending.

    DOMAIN EXPERTISE ENCODED HERE:
    - New hires add 1.35x their salary in TOTAL loaded cost
      (benefits, equipment, onboarding, software licenses).
      This is NOT the same as just adding salary/12.
    - Compliance investment generates 15%/year ongoing audit maintenance cost.
    - Emergency floor: if projected cash drops below this, the floor is breached.

    Args:
        base_burn_monthly:      Current monthly spend (EUR) — from private handbook
        new_hires:              Number of new hires planned
        hire_salary_annual:     Annual salary per hire (EUR)
        infra_spend_onetime:    One-time infrastructure cost (EUR)
        compliance_spend_monthly: New monthly compliance spend (EUR)
        months:                 Projection horizon (months)
        cash_reserves:          Current cash (EUR) — from private handbook, NOT public figure
        emergency_floor:        Floor below which a veto is triggered (default: EUR 500K)

    Returns:
        {
            monthly_burn_trajectory: [float],  one value per month
            runway_months: float,              months until cash_zero
            floor_breach_month: int | None,    month when floor is first breached (None = never)
            cash_zero_month: int | None,       month when cash hits zero (None = never)
            month_1_burn: float,               first-month burn (useful for CEO converter)
            recommendation_signal: str,        'safe' | 'warning' | 'critical'
        }

    Example:
        >>> result = calculate_burn_escalation(
        ...     base_burn_monthly=282_000,    # from Finance private handbook
        ...     new_hires=4,
        ...     hire_salary_annual=85_000,
        ...     infra_spend_onetime=280_000,
        ...     compliance_spend_monthly=180_000,
        ...     months=12,
        ...     cash_reserves=3_100_000,      # private: NOT the public EUR 8M figure
        ... )
        >>> result['runway_months']           # ≈ 6.8 — very different from 27.0 using public figure
        >>> result['floor_breach_month']      # ≈ 3 or 4 — breaches EUR 500K floor early
    """
    # ── Input validation ───────────────────────────────────────────────
    if base_burn_monthly <= 0:
        raise ValueError(f"base_burn_monthly must be > 0, got {base_burn_monthly}")
    if months <= 0:
        raise ValueError(f"months must be > 0, got {months}")
    if cash_reserves < 0:
        raise ValueError(f"cash_reserves cannot be negative, got {cash_reserves}")
    if new_hires < 0:
        raise ValueError(f"new_hires cannot be negative, got {new_hires}")

    # ── Domain-specific constants ─────────────────────────────────────
    LOADED_COST_MULTIPLIER = 1.35   # Benefits, equipment, onboarding, licenses
    COMPLIANCE_MAINTENANCE = 0.15   # 15%/year of compliance investment → ongoing cost

    # ── Monthly cost additions ─────────────────────────────────────────
    hire_monthly_loaded = (new_hires * hire_salary_annual * LOADED_COST_MULTIPLIER) / 12
    compliance_maintenance_monthly = compliance_spend_monthly * COMPLIANCE_MAINTENANCE / 12

    # ── Month-by-month trajectory ──────────────────────────────────────
    trajectory = []
    remaining_cash = cash_reserves
    floor_breach_month = None
    cash_zero_month = None

    for m in range(1, months + 1):
        # Infrastructure is a one-time cost in month 1
        infra_this_month = infra_spend_onetime if m == 1 else 0.0

        monthly_burn = (
            base_burn_monthly
            + hire_monthly_loaded
            + compliance_spend_monthly
            + compliance_maintenance_monthly
            + infra_this_month
        )
        trajectory.append(round(monthly_burn, 2))
        remaining_cash -= monthly_burn

        if floor_breach_month is None and remaining_cash < emergency_floor:
            floor_breach_month = m

        if cash_zero_month is None and remaining_cash <= 0:
            cash_zero_month = m
            break   # no point projecting after zero

    # ── Runway: how many months until cash hits emergency floor ───────
    # More precise: use average monthly burn for non-integer result
    avg_monthly_burn = sum(trajectory) / len(trajectory)
    if avg_monthly_burn > 0:
        runway_to_floor = max(0.0, (cash_reserves - emergency_floor) / avg_monthly_burn)
        runway_to_zero  = max(0.0, cash_reserves / avg_monthly_burn)
    else:
        runway_to_floor = float('inf')
        runway_to_zero  = float('inf')

    # ── Recommendation signal ──────────────────────────────────────────
    if floor_breach_month is not None and floor_breach_month <= 3:
        signal = "critical"
    elif runway_to_floor < 6:
        signal = "warning"
    else:
        signal = "safe"

    return {
        "monthly_burn_trajectory": trajectory,
        "runway_months":           round(runway_to_zero, 1),
        "runway_to_floor_months":  round(runway_to_floor, 1),
        "floor_breach_month":      floor_breach_month,
        "cash_zero_month":         cash_zero_month,
        "month_1_burn":            trajectory[0] if trajectory else 0.0,
        "avg_monthly_burn":        round(avg_monthly_burn, 2),
        "recommendation_signal":   signal,
        "emergency_floor":         emergency_floor,
        "inputs_used": {
            # Log all inputs so the eval can verify private figures were used
            "base_burn_monthly":       base_burn_monthly,
            "new_hires":               new_hires,
            "hire_salary_annual":      hire_salary_annual,
            "loaded_cost_multiplier":  LOADED_COST_MULTIPLIER,
            "cash_reserves":           cash_reserves,
        }
    }

# ── What to do next ──────────────────────────────────────────────────

# This file shows the TOOL PATTERN:
#   - Takes specific numeric inputs
#   - Returns a dict with predictable keys
#   - Same inputs → same output every time (deterministic)
#   - Includes input validation
#   - Uses private knowledge from handbook, NOT public figures
#
# Your department must build 4 tools (see your handbook for F1-F4, E1-E4 etc).
# Each tool follows this same pattern.
#
# To call your tool from your agent, use call_tool() from the base class:
#   result = self.call_tool(self.your_tool_function, param_1=value, param_2=value)
# DO NOT call your tool functions directly — call_tool() logs them automatically.
