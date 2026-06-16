"""Central configuration for the World Cup 2026 predictor."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Free data sources (martj42/international_results, updated continuously) ---
    results_url: str = (
        "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
    )
    goalscorers_url: str = (
        "https://raw.githubusercontent.com/martj42/international_results/master/goalscorers.csv"
    )
    shootouts_url: str = (
        "https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv"
    )

    # How long a cached download stays fresh (hours) before we re-fetch.
    cache_ttl_hours: int = 12
    # How often the background scheduler refreshes data + retrains (hours).
    refresh_interval_hours: int = 12

    # --- Modelling knobs ---
    # Half-life (in days) for time-weighting older matches in Dixon-Coles.
    # ~2 years: recent form matters most but we keep long history signal.
    time_decay_half_life_days: float = 730.0
    # Only train on matches from the last N years (older data is noisy / different eras).
    train_years: int = 8
    # Max goals to enumerate in the score matrix.
    max_goals: int = 10
    # Home advantage in Elo points (ignored for neutral-venue WC matches).
    elo_home_advantage: float = 65.0
    # Blend weight between the two statistical models:
    #   stat 1X2 = dc_blend_weight*DixonColes + (1-dc_blend_weight)*Elo.
    dc_blend_weight: float = 0.65

    # --- Live betting-market odds (The Odds API, free tier) ---
    odds_api_key: str = ""
    odds_sport_key: str = "soccer_fifa_world_cup"
    odds_regions: str = "eu"           # one region keeps request cost = 1/call
    odds_base_url: str = "https://api.the-odds-api.com/v4"
    odds_cache_ttl_hours: int = 12     # never re-fetch more often than this
    # When market odds exist for a match, the final 1X2 becomes:
    #   market_blend_weight*Market + (1-market_blend_weight)*(stat blend).
    # The market is a strong signal (prices in injuries, line-ups, news).
    market_blend_weight: float = 0.5
    # Tournament importance weights for Elo K-factor.
    tournament_weights: dict = {
        "FIFA World Cup": 60.0,
        "FIFA World Cup qualification": 40.0,
        "UEFA Euro": 50.0,
        "UEFA Euro qualification": 35.0,
        "Copa América": 50.0,
        "African Cup of Nations": 45.0,
        "AFC Asian Cup": 45.0,
        "UEFA Nations League": 40.0,
        "CONCACAF Gold Cup": 40.0,
        "Confederations Cup": 45.0,
        "Friendly": 20.0,
    }
    default_tournament_weight: float = 30.0

    # --- Prediction-game scoring (points per stage) ---
    # exact = points for the exact scoreline; direction = points for the right
    # outcome (winner/draw) without the exact score.
    prediction_scoring: dict = {
        "group": {"exact": 3, "direction": 1},
        "r32": {"exact": 5, "direction": 2},
        "r16": {"exact": 5, "direction": 2},
        "qf": {"exact": 8, "direction": 4},
        "sf": {"exact": 10, "direction": 5},
        "third": {"exact": 10, "direction": 5},
        "final": {"exact": 15, "direction": 8},
    }
    default_stage: str = "group"


settings = Settings()
