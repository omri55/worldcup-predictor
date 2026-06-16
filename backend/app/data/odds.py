"""Live betting-market odds from The Odds API (free tier).

A single request returns h2h (1X2) odds for every upcoming World Cup match
across ~24 bookmakers. We:
  * average the bookmakers' implied probabilities, and
  * remove the bookmaker margin ("vig") so the three outcomes sum to 1.

The result is the market's de-vigged probability for each outcome — one of the
strongest predictive signals available, because it already prices in injuries,
line-ups and late news that a results-only model can't see.

Odds are cached on disk and only re-fetched after `odds_cache_ttl_hours`, so we
stay comfortably inside the free monthly request budget.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import requests

from ..config import CACHE_DIR, settings

_CACHE_FILE = CACHE_DIR / "odds.json"

# The Odds API uses a few names that differ from our results dataset.
_TEAM_MAP = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
}


def _norm(name: str) -> str:
    return _TEAM_MAP.get(name, name)


def _devig_match(bookmakers: list[dict], home: str, away: str) -> dict | None:
    """Average de-vigged 1X2 probabilities across all bookmakers for one match."""
    sums = {"home": 0.0, "draw": 0.0, "away": 0.0}
    count = 0
    for bk in bookmakers:
        h2h = next((m for m in bk.get("markets", []) if m["key"] == "h2h"), None)
        if not h2h:
            continue
        prices = {o["name"]: o["price"] for o in h2h["outcomes"]}
        if home not in prices or away not in prices or "Draw" not in prices:
            continue
        # implied prob = 1/decimal_odds, then normalise to strip the margin
        imp = {
            "home": 1.0 / prices[home],
            "draw": 1.0 / prices["Draw"],
            "away": 1.0 / prices[away],
        }
        total = sum(imp.values())
        if total <= 0:
            continue
        for k in sums:
            sums[k] += imp[k] / total
        count += 1

    if count == 0:
        return None
    return {
        "home": round(sums["home"] / count, 4),
        "draw": round(sums["draw"] / count, 4),
        "away": round(sums["away"] / count, 4),
        "bookmakers": count,
    }


def _raw_fetch() -> list[dict]:
    url = f"{settings.odds_base_url}/sports/{settings.odds_sport_key}/odds/"
    params = {
        "apiKey": settings.odds_api_key,
        "regions": settings.odds_regions,
        "markets": "h2h",
        "oddsFormat": "decimal",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _is_cache_fresh() -> bool:
    if not _CACHE_FILE.exists():
        return False
    age_h = (time.time() - _CACHE_FILE.stat().st_mtime) / 3600
    return age_h < settings.odds_cache_ttl_hours


def load_market_odds(force: bool = False) -> dict:
    """Return {frozenset({teamA, teamB}): {teamA: p, teamB: p, 'draw': p, ...}}.

    Order-independent so it matches our fixtures regardless of home/away
    designation. Returns {} (gracefully) if no key is set or the API fails.
    """
    if not settings.odds_api_key:
        return {}

    if not force and _is_cache_fresh():
        try:
            return _deserialize(json.loads(_CACHE_FILE.read_text()))
        except Exception:
            pass

    try:
        raw = _raw_fetch()
    except Exception:
        # On failure, fall back to whatever we last cached.
        if _CACHE_FILE.exists():
            try:
                return _deserialize(json.loads(_CACHE_FILE.read_text()))
            except Exception:
                return {}
        return {}

    odds: dict[frozenset, dict] = {}
    for m in raw:
        home, away = _norm(m["home_team"]), _norm(m["away_team"])
        devigged = _devig_match(m.get("bookmakers", []), m["home_team"], m["away_team"])
        if not devigged:
            continue
        odds[frozenset({home, away})] = {
            home: devigged["home"],
            away: devigged["away"],
            "draw": devigged["draw"],
            "bookmakers": devigged["bookmakers"],
        }

    _CACHE_FILE.write_text(json.dumps(_serialize(odds), ensure_ascii=False))
    return odds


def market_for(odds: dict, home: str, away: str) -> tuple[float, float, float] | None:
    """(p_home, p_draw, p_away) for a fixture, or None if no market odds."""
    rec = odds.get(frozenset({home, away}))
    if not rec or home not in rec or away not in rec:
        return None
    return rec[home], rec["draw"], rec[away]


# --- (de)serialisation: frozenset keys can't be JSON keys, so store as lists ---
def _serialize(odds: dict) -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "entries": [
            {"teams": list(k), "probs": v} for k, v in odds.items()
        ],
    }


def _deserialize(blob: dict) -> dict:
    out = {}
    for e in blob.get("entries", []):
        out[frozenset(e["teams"])] = e["probs"]
    return out
