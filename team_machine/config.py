"""
config.py — NexaAI Team Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHANGE THESE BEFORE STARTING:
  1. TEAM_ID       → your team identifier
  2. COMPANY_NAME  → your company's name
  3. RAG_SERVER_URL → instructor's Mac IP (ask instructor on Monday morning)
"""

# ── Team Identity ──────────────────────────────────────────────────────
# SET THIS: 'team_a' | 'team_b' | 'team_c' | 'team_d'
TEAM_ID = "team_a"

# SET THIS: 'VeriHire AI' | 'TalentLens' | 'ClearPath AI' | 'NexaRecruit'
COMPANY_NAME = "VeriHire AI"

# ── Global RAG Server ─────────────────────────────────────────────────
# SET THIS: Ask the instructor for their Mac's IP address on Monday morning.
# Find it with: ifconfig | grep "inet " (on Mac) or hostname -I (on Linux)
# Example: "http://192.168.1.42:8888"
RAG_SERVER_URL = "http://INSTRUCTOR_MAC_IP:8888"

# ── Ollama Models ──────────────────────────────────────────────────────
MODELS = {
    "ceo":         "qwen2.5:7b",    # CEO needs stronger reasoning
    "finance":     "llama3.2:3b",
    "engineering": "llama3.2:3b",
    "marketing":   "llama3.2:3b",
    "hr":          "llama3.2:3b",
    "legal":       "llama3.2:3b",
}

OLLAMA_BASE_URL = "http://localhost:11434"

# ── Project Paths ──────────────────────────────────────────────────────
import os
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "knowledge_common":   os.path.join(PROJECT_ROOT, "knowledge", "common"),
    "knowledge_finance":  os.path.join(PROJECT_ROOT, "knowledge", "finance"),
    "knowledge_engineering": os.path.join(PROJECT_ROOT, "knowledge", "engineering"),
    "knowledge_marketing":os.path.join(PROJECT_ROOT, "knowledge", "marketing"),
    "knowledge_hr":       os.path.join(PROJECT_ROOT, "knowledge", "hr"),
    "knowledge_legal":    os.path.join(PROJECT_ROOT, "knowledge", "legal"),
    "submissions":        os.path.join(PROJECT_ROOT, "submissions"),
    "logs":               os.path.join(PROJECT_ROOT, "logs"),
    "state":              os.path.join(PROJECT_ROOT, "state"),
}

# ── Submission Settings ────────────────────────────────────────────────
# Do not change these — they are fixed by the evaluation interface
EVAL_SCHEMA_VERSION = "1.0"
