"""Generate a single static data.json with everything the frontend needs.

Run in CI (GitHub Actions) every 12h. The frontend then reads this file instead
of talking to a live backend — so the app can be hosted as a free static site
(GitHub Pages) with no server, no exposed machine, and auto-updating data.

Output: frontend/public/data.json
"""
from __future__ import annotations

import json
from pathlib import Path

from app.engine import engine, _pred_dict

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data.json"


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
        "played": _played_payload(),
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
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    size_kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT} ({size_kb:.0f} KB, {len(predict)} matchups)")


def _played_payload() -> dict:
    matches = engine.played_world_cup(2026)
    hits = sum(1 for m in matches if m.get("prediction_hit"))
    return {
        "matches": matches,
        "model_accuracy_so_far": round(hits / len(matches), 3) if matches else None,
        "hits": hits,
        "total": len(matches),
    }


if __name__ == "__main__":
    main()
