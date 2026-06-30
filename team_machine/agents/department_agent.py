"""
agents/department_agent.py — Base class for all department agents.
Students subclass this for each department.

See agents/example_finance_agent.py for a complete working example
of how to subclass this and implement analyze() + get_output().
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path

from config import OLLAMA_BASE_URL, MODELS, PATHS, TEAM_ID
from global_rag_client import read_global_rag_and_hash, get_market_param, get_active_scenario_id


class DepartmentAgent:
    """Base class. Override analyze() in each department subclass."""

    def __init__(self, dept_name: str):
        self.dept_name       = dept_name
        self.model           = MODELS[dept_name]
        self.rag_content     = {}
        self.rag_hash        = ""
        self.tools_called    = []
        self.tool_outputs    = {}
        self.llm_calls_made  = 0
        self._output         = None

    # ── RAG ──────────────────────────────────────────────────────────

    def read_global_rag(self):
        """ALWAYS call this as the FIRST LINE of analyze(). Reads the live Global RAG."""
        self.rag_content, self.rag_hash = read_global_rag_and_hash()
        active = get_active_scenario_id(self.rag_content)
        print(f"  [{self.dept_name.upper()}] RAG read. Scenario: {active}. Hash: {self.rag_hash[:8]}...")
        return self.rag_content, self.rag_hash

    def read_private_rag(self) -> str:
        """Reads all files from knowledge/{dept_name}/. Returns concatenated text."""
        folder = Path(PATHS.get(f"knowledge_{self.dept_name}", f"knowledge/{self.dept_name}"))
        if not folder.exists():
            return ""
        texts = []
        for f in sorted(folder.rglob("*")):
            if f.is_file() and f.suffix in (".md", ".txt", ".json"):
                texts.append(f"### {f.name}\n{f.read_text(encoding='utf-8')}\n")
        return "\n".join(texts)

    # ── LLM ──────────────────────────────────────────────────────────

    def call_ollama(self, prompt: str, system: str = "") -> str:
        """Calls the department's Ollama model. Tracks call count automatically."""
        payload = {"model": self.model, "prompt": prompt, "system": system, "stream": False}
        try:
            response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=120)
            response.raise_for_status()
            self.llm_calls_made += 1
            return response.json().get("response", "")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot reach Ollama at {OLLAMA_BASE_URL}. "
                "Ensure Ollama is running: ollama serve"
            )

    # ── Tools ─────────────────────────────────────────────────────────

    def call_tool(self, tool_func, **kwargs) -> dict:
        """
        Calls a calculation tool and logs the call and output automatically.
        Always use this instead of calling tool functions directly.

        Example:
            result = self.call_tool(self.my_tool_function, param1=value1, param2=value2)
        """
        tool_name = tool_func.__name__
        try:
            result = tool_func(**kwargs)
            if not isinstance(result, dict):
                raise TypeError(f"Tool {tool_name} must return a dict, got {type(result).__name__}")
            self.tools_called.append(tool_name)
            self.tool_outputs[tool_name] = result
            print(f"  [{self.dept_name.upper()}] Tool: {tool_name} → {list(result.keys())[:4]}")
            return result
        except Exception as e:
            error = {"error": str(e), "tool": tool_name}
            self.tool_outputs[tool_name] = error
            self.tools_called.append(f"{tool_name}:ERROR")
            raise

    # ── Required overrides ────────────────────────────────────────────

    def analyze(self, scenario: str = ""):
        """
        Override this. Pattern (see example_finance_agent.py for full example):
            def analyze(self, scenario=""):
                self.read_global_rag()                        # step 1: always first
                private = self.read_private_rag()            # step 2: private knowledge
                result = self.call_tool(self._my_tool, ...)  # step 3: tools
                text   = self.call_ollama(prompt=..., ...)   # step 4: LLM reasoning
                self._output = { ... all required fields ... } # step 5: output dict
        """
        raise NotImplementedError(f"{self.dept_name}: implement analyze()")

    def get_output(self) -> dict:
        """Returns the complete DepartmentOutput dict. Call after analyze()."""
        if self._output is None:
            raise RuntimeError(f"{self.dept_name}.analyze() must be called before get_output()")
        # Inject automatically tracked fields
        self._output["tools_called"]   = self.tools_called
        self._output["tool_outputs"]   = self.tool_outputs
        self._output["llm_calls_made"] = self.llm_calls_made
        self._output["department"]     = self.dept_name
        self._output["agent_model"]    = self.model
        self._validate_output(self._output)
        return self._output

    def _validate_output(self, output: dict):
        """Quick check before returning. Full validation is in eval_interface."""
        required = [
            "recommendation", "recommended_timeline", "stated_reasoning",
            "confidence", "confidence_method", "information_completeness",
            "known_gaps", "information_withheld", "hard_floor_breached",
            "prediction", "kpi_impact", "hard_constraints", "veto_conditions",
            "external_inputs_used",
        ]
        missing = [f for f in required if f not in output]
        if missing:
            raise ValueError(
                f"[{self.dept_name}] Output missing required fields: {missing}\n"
                "Check Section 6.2 of the Participant Guide."
            )
        if output["recommendation"] not in ("approve", "conditional_approve", "delay", "veto"):
            raise ValueError(f"[{self.dept_name}] Invalid recommendation: {output['recommendation']}")
        if not (0.0 <= output["confidence"] <= 1.0):
            raise ValueError(f"[{self.dept_name}] Confidence must be 0.0-1.0: {output['confidence']}")
        if len(output.get("stated_reasoning", "")) < 100:
            raise ValueError(f"[{self.dept_name}] stated_reasoning must be ≥ 100 chars.")
        if output.get("confidence_method", "").lower().strip() in ("llm estimated", "llm", "model estimated"):
            raise ValueError(f"[{self.dept_name}] confidence_method cannot be 'LLM estimated'.")
