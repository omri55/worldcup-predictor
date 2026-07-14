"""Generate a single static data.json with everything the frontend needs.

Run in CI (GitHub Actions) every 12h. The frontend then reads this file instead
of talking to a live backend — so the app can be hosted as a free static site
(GitHub Pages) with no server, no exposed machine, and auto-updating data.

Output: frontend/public/data.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from app.engine import engine, _pred_dict

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data.json"


def _clean(obj):
    """Recursively replace NaN/Infinity floats with None so the JSON is valid
    (JavaScript's JSON.parse rejects NaN, which Python otherwise emits)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def main() -> None:
    print("Training models + loading data...")
    engine.refresh(force=True)

    print("Building core sections...")
    data = {
        "status": engine.status(),
        "teams": engine.teams(),
        "ranking": engine.ranking(50),
        "upcoming": {
            "matches": engine.upcoming_world_cup(2026),
            "awaiting_result": engine.awaiting_world_cup(2026),
        },
        "played": engine.played_payload(2026),
        "simulation": engine.simulate(4000),
    }

    # Predict tool: all pairwise matchups among the 48 World Cup teams
    # (group-stage scoring) so the "predict any match" tool works offline.
    print("Precomputing pairwise predictions...")
    wc_teams = sorted({t for ts in engine.simulator.groups.values() for t in ts})
    predict = {}
    for h in wc_teams:
        for a in wc_teams:
            if h == a:
                continue
            predict[f"{h}|{a}"] = _pred_dict(engine.predict_match(h, a, stage="group"))
    data["predict"] = predict
    data["wc_teams"] = wc_teams

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # allow_nan=False guarantees valid JSON (raises loudly if any NaN slips past
    # _clean, instead of silently shipping a file the browser can't parse).
    OUT.write_text(
        json.dumps(_clean(data), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    )
    size_kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT} ({size_kb:.0f} KB, {len(predict)} matchups)")


if __name__ == "__main__":
    main()
