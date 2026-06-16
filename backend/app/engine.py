"""Singleton engine: owns the datasets, the trained models and the predictor.

`refresh()` re-downloads data and retrains; the API and the background
scheduler both call into the same instance so predictions stay current.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

import pandas as pd

from .data.loader import (
    Datasets,
    assign_wc_stages,
    load_datasets,
    match_key,
    world_cup_fixtures,
    world_cup_played,
)
from .data.odds import load_market_odds, market_for
from .models.dixon_coles import DixonColesModel
from .models.elo import EloModel
from .models.predictor import MatchPrediction, Predictor
from .models.simulator import TournamentSimulator


class Engine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.datasets: Datasets | None = None
        self.elo: EloModel | None = None
        self.dc: DixonColesModel | None = None
        self.predictor: Predictor | None = None
        self.simulator: TournamentSimulator | None = None
        self._sim_cache: dict | None = None
        self.odds: dict = {}
        self.wc_stages: dict = {}
        self.trained_at: datetime | None = None

    @property
    def ready(self) -> bool:
        return self.predictor is not None

    def refresh(self, force: bool = False) -> None:
        with self._lock:
            ds = load_datasets(force=force)
            elo = EloModel().fit(ds.results)
            dc = DixonColesModel().fit(ds.results)
            self.odds = load_market_odds(force=force)
            self.datasets = ds
            self.elo = elo
            self.dc = dc
            self.predictor = Predictor(dc, elo)

            # Build the tournament simulator from all WC2026 matches
            # (played results + remaining fixtures).
            wc_all = pd.concat(
                [world_cup_played(ds, 2026), world_cup_fixtures(ds, 2026)],
                ignore_index=True,
            )
            self.wc_stages = assign_wc_stages(wc_all)
            # The simulator derives groups from the round-robin, so it must only
            # see group-stage matches (knockout games would merge the groups).
            group_only = wc_all.sort_values("date").head(72)
            self.simulator = (
                TournamentSimulator(dc, elo, group_only) if len(group_only) else None
            )
            self._sim_cache = None  # invalidate cached simulation
            self.trained_at = datetime.now(timezone.utc)

    # ---- queries -----------------------------------------------------------
    def _predict(
        self, home: str, away: str, neutral: bool = True, stage: str = "group"
    ) -> MatchPrediction:
        """Predict a match, folding in live market odds when available."""
        assert self.predictor
        market = market_for(self.odds, home, away)
        rec = self.odds.get(frozenset({home, away})) or {}
        return self.predictor.predict(
            home, away, neutral,
            market=market,
            market_bookmakers=int(rec.get("bookmakers", 0)),
            stage=stage,
        )

    def predict_match(
        self, home: str, away: str, neutral: bool = True, stage: str = "group"
    ) -> MatchPrediction:
        return self._predict(home, away, neutral, stage)

    def simulate(self, n: int = 4000) -> dict:
        """Monte-Carlo tournament simulation (cached until next refresh)."""
        if self.simulator is None:
            return {"simulations": 0, "groups": {}, "teams": []}
        if self._sim_cache is None or self._sim_cache.get("simulations") != n:
            self._sim_cache = self.simulator.run(n=n)
        return self._sim_cache

    def upcoming_world_cup(self, year: int = 2026) -> list[dict]:
        """Only matches that haven't kicked off yet (date >= today)."""
        assert self.datasets and self.predictor
        fx = world_cup_fixtures(self.datasets, year)
        today = pd.Timestamp.now().normalize()
        fx = fx[fx["date"] >= today]
        out = []
        for row in fx.itertuples(index=False):
            stage = self._stage_for(row)
            pred = self._predict(row.home_team, row.away_team, neutral=True, stage=stage)
            out.append(self._fixture_payload(row, pred, played=False))
        return out

    def awaiting_world_cup(self, year: int = 2026) -> list[dict]:
        """Past-dated matches with no result yet in the source data."""
        assert self.datasets
        fx = world_cup_fixtures(self.datasets, year)
        today = pd.Timestamp.now().normalize()
        past = fx[fx["date"] < today].sort_values("date")
        return [
            {
                "date": pd.Timestamp(row.date).strftime("%Y-%m-%d"),
                "home_team": row.home_team,
                "away_team": row.away_team,
            }
            for row in past.itertuples(index=False)
        ]

    def played_world_cup(self, year: int = 2026) -> list[dict]:
        assert self.datasets and self.predictor
        pl = world_cup_played(self.datasets, year)
        out = []
        for row in pl.itertuples(index=False):
            stage = self._stage_for(row)
            pred = self._predict(row.home_team, row.away_team, neutral=True, stage=stage)
            payload = self._fixture_payload(row, pred, played=True)
            actual_score = f"{int(row.home_score)}-{int(row.away_score)}"
            payload["actual"] = {
                "home_score": int(row.home_score),
                "away_score": int(row.away_score),
                "score": actual_score,
            }
            payload["prediction_hit"] = self._hit(row, pred)          # direction
            payload["exact_hit"] = pred.pick_score == actual_score    # exact score
            out.append(payload)
        return out

    def played_payload(self, year: int = 2026) -> dict:
        """Played matches + both accuracy metrics (direction and exact score)."""
        matches = self.played_world_cup(year)
        total = len(matches)
        hits = sum(1 for m in matches if m.get("prediction_hit"))
        exact = sum(1 for m in matches if m.get("exact_hit"))
        return {
            "matches": matches,
            "model_accuracy_so_far": round(hits / total, 3) if total else None,
            "exact_accuracy": round(exact / total, 3) if total else None,
            "hits": hits,
            "exact_hits": exact,
            "total": total,
        }

    def _stage_for(self, row) -> str:
        """Tournament stage of a WC match (group/r32/r16/qf/sf/third/final)."""
        return self.wc_stages.get(
            match_key(row.date, row.home_team, row.away_team), "group"
        )

    def _fixture_payload(self, row, pred: MatchPrediction, played: bool) -> dict:
        return {
            "date": pd.Timestamp(row.date).strftime("%Y-%m-%d"),
            "home_team": row.home_team,
            "away_team": row.away_team,
            "city": getattr(row, "city", None),
            "country": getattr(row, "country", None),
            "played": played,
            "stage": pred.stage,
            "prediction": _pred_dict(pred),
        }

    @staticmethod
    def _hit(row, pred: MatchPrediction) -> bool:
        actual = (
            "home" if row.home_score > row.away_score
            else "away" if row.home_score < row.away_score
            else "draw"
        )
        picks = {
            "home": pred.prob_home,
            "draw": pred.prob_draw,
            "away": pred.prob_away,
        }
        return max(picks, key=picks.get) == actual

    def ranking(self, top: int = 50) -> list[dict]:
        assert self.elo
        return [
            {"rank": i + 1, "team": t, "elo": round(r, 1)}
            for i, (t, r) in enumerate(self.elo.ranking(top))
        ]

    def teams(self) -> list[str]:
        assert self.elo
        return sorted(self.elo.ratings.keys())

    def status(self) -> dict:
        return {
            "ready": self.ready,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            "data_loaded_at": (
                self.datasets.loaded_at.isoformat() if self.datasets else None
            ),
            "matches_in_training": (
                int(len(self.datasets.results)) if self.datasets else 0
            ),
            "teams_rated": len(self.elo.ratings) if self.elo else 0,
            "dc_home_advantage": round(self.dc.home_adv, 3) if self.dc else None,
            "market_odds_enabled": bool(self.odds),
            "matches_with_market_odds": len(self.odds),
        }


def _pred_dict(p: MatchPrediction) -> dict:
    return {
        "prob_home": p.prob_home,
        "prob_draw": p.prob_draw,
        "prob_away": p.prob_away,
        "xg_home": p.xg_home,
        "xg_away": p.xg_away,
        "likely_score": p.likely_score,
        "likely_score_prob": p.likely_score_prob,
        "top_scores": p.top_scores,
        "over_2_5": p.over_2_5,
        "under_2_5": p.under_2_5,
        "btts_yes": p.btts_yes,
        "btts_no": p.btts_no,
        "margins": p.margins,
        "stage": p.stage,
        "pick_score": p.pick_score,
        "pick_outcome": p.pick_outcome,
        "pick_ev": p.pick_ev,
        "safe_score": p.safe_score,
        "safe_outcome": p.safe_outcome,
        "safe_ev": p.safe_ev,
        "aggressive_score": p.aggressive_score,
        "aggressive_outcome": p.aggressive_outcome,
        "aggressive_ev": p.aggressive_ev,
        "recommendation": p.recommendation,
        "confidence": p.confidence,
        "elo_home": p.elo_home,
        "elo_away": p.elo_away,
        "market_used": p.market_used,
        "market_bookmakers": p.market_bookmakers,
    }


engine = Engine()
