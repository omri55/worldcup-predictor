"""Download, cache and parse the free international-football datasets.

Source: https://github.com/martj42/international_results (CC0, updated continuously).
A single CSV gives us:
  * the full history of international results (training data), and
  * the upcoming World Cup 2026 fixtures (rows with NA scores).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from ..config import CACHE_DIR, settings


@dataclass
class Datasets:
    """Parsed, ready-to-use frames."""

    results: pd.DataFrame      # only played matches (scores present)
    fixtures: pd.DataFrame     # only future / unplayed matches (NA scores)
    goalscorers: pd.DataFrame
    shootouts: pd.DataFrame
    loaded_at: datetime


def _download(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def _cached_path(url: str) -> Path:
    return CACHE_DIR / Path(url).name


def _is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    return age_hours < settings.cache_ttl_hours


def fetch_csv(url: str, force: bool = False) -> pd.DataFrame:
    """Return a CSV as a DataFrame, downloading only when the cache is stale."""
    path = _cached_path(url)
    if force or not _is_fresh(path):
        try:
            _download(url, path)
        except Exception:
            if not path.exists():
                raise  # nothing cached to fall back to
            # otherwise: serve stale cache rather than crash
    return pd.read_csv(path)


def load_datasets(force: bool = False) -> Datasets:
    raw = fetch_csv(settings.results_url, force=force)
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw = raw.dropna(subset=["date"])
    raw["neutral"] = raw["neutral"].astype(str).str.upper().eq("TRUE")

    played_mask = raw["home_score"].notna() & raw["away_score"].notna()
    results = raw[played_mask].copy()
    results["home_score"] = results["home_score"].astype(int)
    results["away_score"] = results["away_score"].astype(int)

    fixtures = raw[~played_mask].copy()

    try:
        goalscorers = fetch_csv(settings.goalscorers_url, force=force)
        goalscorers["date"] = pd.to_datetime(goalscorers["date"], errors="coerce")
    except Exception:
        goalscorers = pd.DataFrame()

    try:
        shootouts = fetch_csv(settings.shootouts_url, force=force)
        shootouts["date"] = pd.to_datetime(shootouts["date"], errors="coerce")
    except Exception:
        shootouts = pd.DataFrame()

    return Datasets(
        results=results.reset_index(drop=True),
        fixtures=fixtures.reset_index(drop=True),
        goalscorers=goalscorers,
        shootouts=shootouts,
        loaded_at=datetime.now(timezone.utc),
    )


def world_cup_fixtures(ds: Datasets, year: int = 2026) -> pd.DataFrame:
    """Upcoming World Cup matches for the given year, oldest first."""
    f = ds.fixtures
    mask = (f["tournament"] == "FIFA World Cup") & (f["date"].dt.year == year)
    return f[mask].sort_values("date").reset_index(drop=True)


def world_cup_played(ds: Datasets, year: int = 2026) -> pd.DataFrame:
    """Already-played World Cup matches for the given year (results in)."""
    r = ds.results
    mask = (r["tournament"] == "FIFA World Cup") & (r["date"].dt.year == year)
    return r[mask].sort_values("date").reset_index(drop=True)


# 48-team World Cup: 12 groups x 6 = 72 group matches, then the knockout bracket.
GROUP_STAGE_MATCHES = 72
KNOCKOUT_ORDER = (
    ["r32"] * 16 + ["r16"] * 8 + ["qf"] * 4 + ["sf"] * 2 + ["third"] + ["final"]
)


def match_key(date, home: str, away: str) -> tuple[str, str, str]:
    return (pd.Timestamp(date).strftime("%Y-%m-%d"), home, away)


def assign_wc_stages(wc_all: pd.DataFrame) -> dict[tuple, str]:
    """Map every World Cup match to its stage.

    Self-calibrating from the bracket structure: the first 72 matches (by date)
    are the group stage; the remainder are the knockout rounds in order. No
    hard-coded dates, so it works as knockout fixtures appear during the event.
    """
    df = wc_all.sort_values("date").reset_index(drop=True)
    stages: dict[tuple, str] = {}
    for pos, row in enumerate(df.itertuples(index=False)):
        key = match_key(row.date, row.home_team, row.away_team)
        if pos < GROUP_STAGE_MATCHES:
            stages[key] = "group"
        else:
            ko = pos - GROUP_STAGE_MATCHES
            stages[key] = KNOCKOUT_ORDER[ko] if ko < len(KNOCKOUT_ORDER) else "final"
    return stages
