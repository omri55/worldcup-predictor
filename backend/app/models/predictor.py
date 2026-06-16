"""Blends Dixon-Coles + Elo into a single rich match prediction.

Dixon-Coles supplies the full score distribution (and therefore exact score,
over/under, BTTS, clean sheets). Elo supplies an independent strength-based
1X2 estimate. The two 1X2 views are blended for a more robust, less
overfit final probability.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..config import settings
from .dixon_coles import DixonColesModel
from .elo import EloModel


def _extend_to_extra_time(mat90: np.ndarray, lam: float, mu: float) -> np.ndarray:
    """Turn a 90' score distribution into the after-extra-time (120') one.

    A match level after 90' plays ~30' more (1/3 of the goal rate). Decisive
    90' results stand; a still-level result after ET also stands (penalties are
    excluded from the recorded score).
    """
    from scipy.stats import poisson

    m = mat90.shape[0]
    eh = poisson.pmf(np.arange(m), lam / 3.0)
    ea = poisson.pmf(np.arange(m), mu / 3.0)
    out = np.zeros_like(mat90)
    for i in range(m):
        for j in range(m):
            p = mat90[i, j]
            if p <= 0:
                continue
            if i != j:
                out[i, j] += p  # decided in regulation
            else:
                for gh in range(m - i):      # level at 90' -> add ET goals
                    for ga in range(m - j):
                        out[i + gh, j + ga] += p * eh[gh] * ea[ga]
    s = out.sum()
    return out / s if s > 0 else out


@dataclass
class MatchPrediction:
    home_team: str
    away_team: str
    neutral: bool
    # 1X2
    prob_home: float
    prob_draw: float
    prob_away: float
    # expected goals
    xg_home: float
    xg_away: float
    # most likely exact score + its probability
    likely_score: str
    likely_score_prob: float
    top_scores: list[dict] = field(default_factory=list)
    # markets
    over_2_5: float = 0.0
    under_2_5: float = 0.0
    btts_yes: float = 0.0
    btts_no: float = 0.0
    # win-margin breakdown (home by 2+, by 1, draw, away by 1, away by 2+)
    margins: dict = field(default_factory=dict)
    # EV-optimal pick for a prediction game (depends on the stage's scoring)
    stage: str = "group"
    pick_score: str = ""          # balanced: the EV-maximising scoreline
    pick_outcome: str = ""        # "home" / "draw" / "away"
    pick_ev: float = 0.0          # expected points from the balanced pick
    # leading strategy: lowest-variance grab of the direction points
    safe_score: str = ""
    safe_outcome: str = ""
    safe_ev: float = 0.0
    # trailing strategy: high-upside contrarian pick on close games
    aggressive_score: str = ""
    aggressive_outcome: str = ""
    aggressive_ev: float = 0.0
    # human-readable recommendation
    recommendation: str = ""
    confidence: float = 0.0
    # supporting ratings
    elo_home: float = 0.0
    elo_away: float = 0.0
    # did live betting-market odds feed into this prediction?
    market_used: bool = False
    market_bookmakers: int = 0


class Predictor:
    def __init__(self, dc: DixonColesModel, elo: EloModel) -> None:
        self.dc = dc
        self.elo = elo

    def predict(
        self,
        home: str,
        away: str,
        neutral: bool = True,
        market: tuple[float, float, float] | None = None,
        market_bookmakers: int = 0,
        stage: str = "group",
    ) -> MatchPrediction:
        mat = self.dc.score_matrix(home, away, neutral)
        # Knockout matches are decided after extra time (120'), excluding
        # penalties — matching the prediction-league rule. If the score is level
        # after 90', play ~30' more (1/3 of the goal rate); a still-level result
        # stands (penalties don't count). Group games are 90' only.
        if stage != "group":
            lam90, mu90 = self.dc.expected_goals(home, away, neutral)
            mat = _extend_to_extra_time(mat, lam90, mu90)
        m = mat.shape[0]

        # 1X2 from the score matrix
        p_home_dc = float(np.tril(mat, -1).sum())   # home goals > away goals
        p_away_dc = float(np.triu(mat, 1).sum())
        p_draw_dc = float(np.trace(mat))

        # statistical 1X2: blend Dixon-Coles with Elo
        p_home_e, p_draw_e, p_away_e = self.elo.win_draw_loss(home, away, neutral)
        w = settings.dc_blend_weight
        p_home = w * p_home_dc + (1 - w) * p_home_e
        p_draw = w * p_draw_dc + (1 - w) * p_draw_e
        p_away = w * p_away_dc + (1 - w) * p_away_e

        # fold in the live market odds when available (strongest single signal)
        market_used = market is not None
        if market_used:
            mw = settings.market_blend_weight
            mh, md, ma = market
            p_home = mw * mh + (1 - mw) * p_home
            p_draw = mw * md + (1 - mw) * p_draw
            p_away = mw * ma + (1 - mw) * p_away

        s = p_home + p_draw + p_away
        p_home, p_draw, p_away = p_home / s, p_draw / s, p_away / s

        xg_home, xg_away = self.dc.expected_goals(home, away, neutral)

        # Re-weight the Dixon-Coles score matrix so its win/draw/loss totals
        # match the BLENDED 1X2 (which includes Elo + market), while keeping the
        # within-outcome score shape from Dixon-Coles. All score-level outputs
        # (exact score, picks) are then consistent with the blended view.
        adj = mat.copy()
        scale = {
            "home": p_home / p_home_dc if p_home_dc > 0 else 0.0,
            "draw": p_draw / p_draw_dc if p_draw_dc > 0 else 0.0,
            "away": p_away / p_away_dc if p_away_dc > 0 else 0.0,
        }
        for i in range(m):
            for j in range(m):
                region = "home" if i > j else "away" if i < j else "draw"
                adj[i, j] *= scale[region]
        ssum = adj.sum()
        if ssum > 0:
            adj /= ssum

        # top exact scores (from the blended distribution)
        flat = [(i, j, adj[i, j]) for i in range(m) for j in range(m)]
        flat.sort(key=lambda t: t[2], reverse=True)
        top = flat[:5]
        likely = top[0]
        top_scores = [{"score": f"{i}-{j}", "prob": round(p, 4)} for i, j, p in top]

        # totals/BTTS stay on the pure Dixon-Coles matrix (market informs the
        # winner, not the number of goals).
        over = btts = 0.0
        for i in range(m):
            for j in range(m):
                if i + j >= 3:
                    over += mat[i, j]
                if i >= 1 and j >= 1:
                    btts += mat[i, j]

        # win-margin breakdown (on the blended matrix, consistent with 1X2)
        margins = {"home2": 0.0, "home1": 0.0, "draw": 0.0, "away1": 0.0, "away2": 0.0}
        for i in range(m):
            for j in range(m):
                d = i - j
                if d >= 2:
                    margins["home2"] += adj[i, j]
                elif d == 1:
                    margins["home1"] += adj[i, j]
                elif d == 0:
                    margins["draw"] += adj[i, j]
                elif d == -1:
                    margins["away1"] += adj[i, j]
                else:
                    margins["away2"] += adj[i, j]
        margins = {k: round(float(v), 4) for k, v in margins.items()}

        # --- EV-optimal pick for the prediction game ---
        scoring = settings.prediction_scoring.get(
            stage, settings.prediction_scoring[settings.default_stage]
        )
        ex_pts, dir_pts = scoring["exact"], scoring["direction"]
        dir_prob = {"home": p_home, "draw": p_draw, "away": p_away}

        def region(i, j):
            return "home" if i > j else "away" if i < j else "draw"

        def ev_of(ij):
            i, j = ij
            d = region(i, j)
            return ex_pts * adj[i, j] + dir_pts * (dir_prob[d] - adj[i, j])

        def best_score_in(direction):
            return max(
                ((i, j) for i in range(m) for j in range(m) if region(i, j) == direction),
                key=lambda ij: adj[ij[0], ij[1]],
            )

        # balanced: maximise expected points across all scorelines
        best_ev, best_ij, best_dir = -1.0, (0, 0), "draw"
        for i in range(m):
            for j in range(m):
                ev = ev_of((i, j))
                if ev > best_ev:
                    best_ev, best_ij, best_dir = ev, (i, j), region(i, j)
        pick_score = f"{best_ij[0]}-{best_ij[1]}"

        # leading/safe: most-likely score inside the most-likely outcome
        dirs_sorted = sorted(dir_prob, key=dir_prob.get, reverse=True)
        top_dir = dirs_sorted[0]
        safe_ij = best_score_in(top_dir)
        safe_score = f"{safe_ij[0]}-{safe_ij[1]}"

        # trailing/aggressive: on close games take the second-best outcome's best
        # score (contrarian, high upside). On a clear favourite (>=55%) there's
        # nothing to gain, so keep the balanced pick.
        if dir_prob[top_dir] >= 0.55:
            agg_ij, agg_dir = best_ij, best_dir
        else:
            agg_dir = dirs_sorted[1]
            agg_ij = best_score_in(agg_dir)
        aggressive_score = f"{agg_ij[0]}-{agg_ij[1]}"

        rec, conf = self._recommend(
            home, away, p_home, p_draw, p_away, best_dir, pick_score, best_ev, over
        )

        return MatchPrediction(
            home_team=home,
            away_team=away,
            neutral=neutral,
            prob_home=round(p_home, 4),
            prob_draw=round(p_draw, 4),
            prob_away=round(p_away, 4),
            xg_home=round(xg_home, 2),
            xg_away=round(xg_away, 2),
            likely_score=f"{likely[0]}-{likely[1]}",
            likely_score_prob=round(float(likely[2]), 4),
            top_scores=top_scores,
            over_2_5=round(float(over), 4),
            under_2_5=round(float(1 - over), 4),
            btts_yes=round(float(btts), 4),
            btts_no=round(float(1 - btts), 4),
            margins=margins,
            stage=stage,
            pick_score=pick_score,
            pick_outcome=best_dir,
            pick_ev=round(float(best_ev), 3),
            safe_score=safe_score,
            safe_outcome=top_dir,
            safe_ev=round(float(ev_of(safe_ij)), 3),
            aggressive_score=aggressive_score,
            aggressive_outcome=agg_dir,
            aggressive_ev=round(float(ev_of(agg_ij)), 3),
            recommendation=rec,
            confidence=round(conf, 4),
            elo_home=round(self.elo.rating(home), 1),
            elo_away=round(self.elo.rating(away), 1),
            market_used=market_used,
            market_bookmakers=market_bookmakers,
        )

    def _recommend(self, home, away, p_home, p_draw, p_away, pick_dir, pick_score, ev, over):
        outcomes = {"home": p_home, "draw": p_draw, "away": p_away}
        best_p = outcomes[pick_dir]
        if pick_dir == "home":
            label = f"ניצחון {home}"
        elif pick_dir == "away":
            label = f"ניצחון {away}"
        else:
            label = "תיקו"
        # The pick scoreline already encodes the outcome, so this never
        # contradicts itself (no more "Ecuador win, 0-0").
        rec = f"נחש {pick_score} ({label}) · תוחלת {ev:.2f} נק'"
        # confidence: how decisive is the top outcome vs a coin-flip baseline
        conf = float(min(1.0, max(0.0, (best_p - 0.33) / 0.5)))
        return rec, conf
