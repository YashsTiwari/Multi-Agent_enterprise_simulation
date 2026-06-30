"""
global_rag_client.py — Global RAG Reader
Reads live market conditions, scenario updates, and competitor intelligence
from the instructor's Mac server.

MANDATORY USAGE IN EVERY AGENT:
    def analyze(self, scenario=""):
        rag_content, rag_hash = read_global_rag_and_hash()   # ← first line
        market_share = get_market_param(rag_content, "eu_available_market_share")
        self._rag_hash = rag_hash                             # ← store for submission
        ...
"""

import hashlib
import json
import time
import requests
from typing import Tuple, Dict, Optional

from config import RAG_SERVER_URL

# ── Module-level cache: used if server temporarily unreachable ─────────
_rag_cache: Optional[Tuple[Dict[str, str], str]] = None


# ── FIX 1: Deterministic, normalized hash ─────────────────────────────
def _normalize(content: str) -> str:
    """
    Normalize file content before hashing.
    Prevents divergence from:
      - Windows vs Unix line endings (\r\n vs \n)
      - Trailing newlines added by editors
      - UTF-8 BOM markers
    """
    return content.replace('\r\n', '\n').replace('\r', '\n').strip()


def _compute_hash(files: Dict[str, str]) -> str:
    """
    Compute a deterministic SHA256 over all RAG file contents.

    Format: SHA256( sorted_key1 + "||" + normalized_content1 + "\\n" + ... )

    The "||" separator prevents key-value collisions.
    Sorted iteration ensures order-independence.
    Only .md and .json files are included (same filter as the server).
    """
    parts = []
    for key in sorted(files.keys()):
        if key.endswith('.md') or key.endswith('.json'):
            parts.append(f"{key}||{_normalize(files[key])}")
    combined = "\n".join(parts)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


# ── FIX 2: Retry + cache fallback ─────────────────────────────────────
def read_global_rag_and_hash(
    retries: int = 3,
    retry_delay: float = 2.0,
) -> Tuple[Dict[str, str], str]:
    """
    Reads ALL files from the Global RAG server.

    Returns:
        files:         dict {relative_path: content} for all RAG files
        snapshot_hash: SHA256 of all content — MUST be included in your submission

    Retry behaviour:
        Tries up to `retries` times with `retry_delay` seconds between attempts.
        On total failure, returns last cached RAG if available (with a warning).
        This prevents a 5-second WiFi flicker from destroying a full agent run.

    Raises:
        RuntimeError: Only if all retries fail AND there is no cache.
    """
    global _rag_cache

    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(
                f"{RAG_SERVER_URL}/rag/all",
                timeout=10,
            )
            response.raise_for_status()
            files = response.json()

            h = _compute_hash(files)
            _rag_cache = (files, h)   # update cache on success
            return files, h

        except requests.exceptions.Timeout:
            last_error = "Request timed out after 10s."
        except requests.exceptions.ConnectionError as e:
            last_error = str(e)
        except Exception as e:
            last_error = str(e)

        if attempt < retries - 1:
            print(f"[RAG] Attempt {attempt + 1}/{retries} failed: {last_error}. "
                  f"Retrying in {retry_delay}s...")
            time.sleep(retry_delay)

    # All retries exhausted — try the cache
    if _rag_cache is not None:
        print(
            f"\n[RAG] ⚠  WARNING: Cannot reach RAG server after {retries} attempts.\n"
            f"[RAG]    Using CACHED content from last successful read.\n"
            f"[RAG]    Your rag_snapshot_hash will reflect the cached state.\n"
            f"[RAG]    Fix: check that {RAG_SERVER_URL} is reachable.\n"
        )
        return _rag_cache

    # No cache either — this is a hard failure
    raise RuntimeError(
        f"\n[RAG] Cannot reach Global RAG server at {RAG_SERVER_URL}\n"
        f"      after {retries} attempts. Last error: {last_error}\n\n"
        f"      Checklist:\n"
        f"      1. Is rag_server.py running on the instructor's Mac?\n"
        f"      2. Is your machine on the same WiFi network?\n"
        f"      3. Is RAG_SERVER_URL correct in config.py?\n"
        f"         Current value: {RAG_SERVER_URL}\n"
        f"      4. Try: curl {RAG_SERVER_URL}/status\n"
    )


# ── Convenience extractors ────────────────────────────────────────────

def get_market_param(rag_content: Dict[str, str], param: str, default=None):
    """
    Extracts a parameter from market/market_state.json.

    YOUR TOOLS MUST USE THIS — do not hardcode market values.
    Values change after every team release and every hurdle injection.

    Example:
        market_share = get_market_param(rag_content, "eu_available_market_share")
        # → 0.88 (after Team A released)
        # → would have been 1.0 if hardcoded at workshop start
    """
    raw = rag_content.get("market/market_state.json", "{}")
    try:
        state = json.loads(raw)
        return state.get(param, default)
    except json.JSONDecodeError:
        return default


def get_market_state(rag_content: Dict[str, str]) -> dict:
    """Returns the full market state dict."""
    raw = rag_content.get("market/market_state.json", "{}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def get_active_scenario(rag_content: Dict[str, str]) -> str:
    """Returns full text of the active scenario."""
    return rag_content.get("scenario/active_scenario.md", "")


def get_active_scenario_id(rag_content: Dict[str, str]) -> str:
    """
    Returns the scenario ID (e.g. 'H0', 'H1', 'H2', 'H3').
    Reads from the first line: '# ACTIVE SCENARIO — H1'
    """
    scenario = get_active_scenario(rag_content)
    for line in scenario.split("\n"):
        if line.startswith("# ACTIVE SCENARIO"):
            parts = line.split("—")
            if len(parts) >= 2:
                return parts[1].strip().split()[0]  # first token after —
    return "H0"


def get_competitor_releases(rag_content: Dict[str, str]) -> list:
    """Returns competitor release bulletins, sorted by release number."""
    releases = [
        {"path": k, "content": v}
        for k, v in rag_content.items()
        if k.startswith("releases/") and k.endswith(".md")
    ]
    return sorted(releases, key=lambda x: x["path"])


def get_prediction_accuracy_report(rag_content: Dict[str, str], round_number: int) -> str:
    """Returns the prediction accuracy report for calibration tracking."""
    return rag_content.get(f"scores/prediction_accuracy_round_{round_number}.md", "")


def get_regulation_text(rag_content: Dict[str, str]) -> str:
    """Returns the EU AI Act summary and any regulatory updates."""
    parts = []
    for k, v in rag_content.items():
        if k.startswith("regulation/"):
            parts.append(v)
    return "\n\n".join(parts)


def verify_rag_connection() -> bool:
    """Quick connectivity check. Call at startup to give early warning."""
    try:
        r = requests.get(f"{RAG_SERVER_URL}/status", timeout=5)
        data = r.json()
        print(f"[RAG] ✓ Connected. Files: {data['file_count']}, "
              f"Hash prefix: {data['current_hash'][:12]}...")
        return True
    except Exception as e:
        print(f"[RAG] ✗ Cannot connect to {RAG_SERVER_URL}: {e}")
        return False
