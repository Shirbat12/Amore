"""One-shot diagnostic: why does a given user see / not see insights?

Run from the repo root:
    python tools/diagnose_user.py yael.c40@gmail.com

Prints a clear verdict covering the common causes: data stored under a raw id,
dates with no features, or code/server out of date.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

# Allow running as `python tools/diagnose_user.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import config
from server.db import relational
from server.pipeline.presentation import build_dashboard
from server.pipeline.questionnaire_loader import resolve_user_id


def main(identifier: str) -> None:
    uid = resolve_user_id(identifier)
    print("=" * 60)
    print(f"Diagnosing: {identifier!r}")
    print(f"Canonical id (what the DB should use): {uid}")
    print("=" * 60)

    conn = sqlite3.connect(config.SQLITE_PATH)
    canon = conn.execute("SELECT COUNT(*) FROM dates WHERE user_id=?", (uid,)).fetchone()[0]
    raw = conn.execute("SELECT COUNT(*) FROM dates WHERE user_id=?", (str(identifier),)).fetchone()[0]
    conn.close()

    print(f"dates under canonical id : {canon}")
    print(f"dates under RAW id        : {raw}")

    if canon == 0 and raw > 0:
        print("\nVERDICT: data is stored under the RAW id, not the canonical one")
        print("  -> it was written before the id-consistency fix. It needs re-keying.")
        print("     (tell Shir — there's a one-line migration for this.)")
        return
    if canon == 0 and raw == 0:
        print("\nVERDICT: this user has NO dates in THIS database.")
        print("  -> the dates are on a different machine, or under a different email.")
        return

    history = relational.get_history(uid)
    with_feature = sum(1 for d in history if d.profile or d.topic_tags or d.vibe_tags)
    print(f"dates carrying any feature (profile/topic/vibe tags): {with_feature}/{len(history)}")

    dash = build_dashboard(history)
    has_fix = "experiment_analysis" in dash
    rev = dash.get("experiment_analysis", {}).get("revealed_preferences", {})
    patterns = [p for p in rev.get("positive_patterns", []) + rev.get("negative_patterns", [])
                if p.get("appearances", 0) >= 2]
    print(f"code has the insights fix (experiment_analysis present): {has_fix}")
    print(f"insight patterns this code would produce: {len(patterns)}")

    print("\nVERDICT:")
    if not has_fix:
        print("  Code is OUT OF DATE -> run: git pull, then RESTART the backend.")
    elif with_feature == 0:
        print("  The dates have NO features (no profile, no topic/vibe tags).")
        print("  -> fill the form's topic & vibe word-banks (or open it from the extension).")
    elif patterns:
        print("  Data + code are FINE. If the dashboard still shows the generic line,")
        print("  the running server is using OLD code -> RESTART uvicorn, then hard-refresh")
        print("  the dashboard (Ctrl+F5).")
    else:
        print("  Dates exist but no feature repeats across >=2 dates yet -> add a few more")
        print("  dates that share a topic/vibe tag.")
    print("=" * 60)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo_user")
