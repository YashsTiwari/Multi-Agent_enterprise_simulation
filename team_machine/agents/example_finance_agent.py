"""
agents/example_finance_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PATTERN GUIDE — not working code. You build this.

Every department agent follows the same four-step structure.
This file describes that structure. Your job is to implement it
for your department using your private knowledge and your tools.

THE FOUR STEPS (implement these in your agent's analyze() method):

    def analyze(self, scenario=""):

        # STEP 1 — Read the Global RAG (always the first line)
        # This populates self.rag_content and self.rag_hash.
        # Never hardcode market values — read them here at runtime.
        self.read_global_rag()
        market_share = get_market_param(self.rag_content, "eu_available_market_share")

        # STEP 2 — Read your private knowledge folder
        # Returns all files from knowledge/{your_dept}/ as a string.
        # This is the information only your department has.
        private_knowledge = self.read_private_rag()

        # STEP 3 — Call your calculation tools (via call_tool, NOT directly)
        # call_tool() automatically logs the call and output for traceability.
        # Tools must be deterministic Python functions — no LLM calls inside.
        # Your handbook specifies which tools to build (F1-F4, E1-E4, etc.)
        result = self.call_tool(
            self.your_tool_function,   # the tool method you implement
            param_1 = value_from_handbook,
            param_2 = value_from_rag,
            # Cross-dept: Finance and Engineering use HR's output as an input.
            # Set these via set_cross_dept_input() before analyze() is called.
        )

        # STEP 4 — Use LLM to reason about tool outputs
        # The LLM explains and contextualises the tool results.
        # It does NOT compute numbers — your tools already did that.
        reasoning = self.call_ollama(
            prompt = f"Tool returned: {result}. Scenario: {scenario[:300]}. Recommend...",
            system = "You are the [YOUR DEPT] department of an AI company. Your KPIs: ..."
        )

        # STEP 5 — Build the complete output dict
        # Every field in Section 6.2 of the Participant Guide is required.
        # hard_floor_breached: did this scenario cross your veto condition?
        # external_inputs_used: which other dept's outputs did you use as tool inputs?
        # prediction: one quantitative prediction for calibration tracking.
        self._output = {
            "department":               "[your_dept]",
            "recommendation":           "approve|conditional_approve|delay|veto",
            "recommended_timeline":     "30d|90d|Q3|conditional",
            "conditions":               [],
            "stated_reasoning":         f"[YOUR_TOOL].returned [KEY_VALUE], therefore... (cite tool names and values)",
            "key_assumptions":          ["assumption 1", "assumption 2"],
            "confidence":               0.0,          # 0.0 to 1.0
            "confidence_method":        "describe HOW, not 'LLM estimated'",
            "information_completeness": 0.0,          # 1.0 = shared everything
            "known_gaps":               [],           # what you know but are not sharing
            "information_withheld":     False,
            "hard_floor_breached":      False,        # True if your veto condition triggers
            "hard_floor_detail":        "",
            "external_inputs_used":     {"hr": None, "engineering": None},
            "prediction": {
                "predicted_value":       0.0,
                "prediction_unit":       "describe the unit",
                "confidence_interval":   [0.0, 0.0],
                "outcome_check_trigger": "after_round_1_evaluation",
            },
            # tools_called and tool_outputs are injected automatically by get_output()
            # from self.tools_called and self.tool_outputs set in call_tool().
            # Do not set them here.
            "kpi_impact": {
                "own_kpi_delta":         0.0,
                "company_kpi_delta":     0.0,
                "tradeoff_description":  "explain the tradeoff if signs differ",
            },
            "hard_constraints":         ["your non-negotiable condition"],
            "veto_conditions":          ["exact condition that triggers your veto"],
        }

WHAT TO DO WITH THIS FILE:
    1. Create agents/finance_agent.py (or your dept name)
    2. class FinanceAgent(DepartmentAgent):
    3. Implement analyze() following the four steps above
    4. Add your tool methods (F1-F4 from the handbook)
    5. Run python main.py --validate-only to check schema

The hardest part is NOT the code — it is deciding:
    - What does your tool compute, and what inputs does it need?
    - What private handbook figures go into each tool?
    - Where is your hard floor, and how does the tool detect it?
    - What is your one quantitative prediction for calibration tracking?

Those decisions require your domain expertise. No LLM can make them for you.
"""

# This file is intentionally not runnable.
# Build your own agent in agents/your_dept_agent.py
