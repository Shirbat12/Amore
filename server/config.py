"""Central configuration constants for A-MORE.

Every tunable referenced across the pipeline lives here so the rest of the code
never hard-codes a threshold. Maps to project book section 2.3 / 4.1.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- paths ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / ".data"                  # local store, git-ignored
DATA_DIR.mkdir(exist_ok=True)
SQLITE_PATH = DATA_DIR / "amore.db"             # relational store
DOCSTORE_DIR = DATA_DIR / "documents"           # json document store

# --- learning core (section 2.3.3) --------------------------------------
# Below this many dates per user the per-user Ridge model is unstable, so we
# fall back to a population prior and report low confidence (cold start).
MIN_DATES = 8
# Ridge regularization strengths searched per-user via leave-one-out CV.
ALPHA_GRID = (0.1, 1.0, 10.0, 100.0)
# Confidence tiers by amount of accrued personal history.
CONF_MEDIUM_DATES = MIN_DATES
CONF_HIGH_DATES = 2 * MIN_DATES

# --- NLP / Gemini (section 2.3.1) ---------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MAX_RETRIES = 3                                 # Gemini sometimes breaks schema

# --- correlation / explanation ------------------------------------------
FDR_METHOD = "fdr_bh"                            # Benjamini-Hochberg
SIGNIFICANT_Q = 0.10                             # q-value cutoff for "real" links

# --- evaluation success criteria (section 4.1) --------------------------
TARGET_PREDICTION_RHO = 0.4
TARGET_SUS = 68.0
TARGET_VIBE_RESPONSE_RATE = 0.60
TARGET_CONVERSION_UPLIFT = 0.20                 # +20% over personal baseline
