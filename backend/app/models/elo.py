"""World-Football style Elo ratings, computed from the full results history.

Follows the eloratings.net approach:
  * Expected score  We = 1 / (1 + 10^(-dr/400)),  dr = rating diff (+ home adv).
  * Update          R' = R + K * G * (W - We)
        K  = tournament importance weight
        G  = goal-difference multiplier (blowouts move ratings more)
        W  = match result (1 win / 0.5 draw / 0 loss)
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from ..config import settings

BASE_RATING = 1500.0


def _goal_diff_multiplier(goal_diff: int) -> float:
    gd = abs(goal_diff)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0  # 3 -> 1.75, 4 -> 1.875, ...


def _k_for(tournament: str) -> float:
    return settings.tournament_weights.get(
        tournament, settings.default_tournament_weight
    )


class EloModel:
    """Sequentially processes every historical match to build current ratings."""

    def __init__(self) -> None:
        self.ratings: dict[str, float] = defaultdict(lambda: BASE_RATING)
        self.last_played: dict[str, pd.Timestamp] = {}

    def expected(self, home: str, away: str, neutral: bool) -> float:
        ha = 0.0 if neutral else settings.elo_home_advantage
        dr = (self.ratings[home] + ha) - self.ratings[away]
        return 1.0 / (1.0 + 10 ** (-dr / 400.0))

    def fit(self, results: pd.DataFrame) -> "EloModel":
        for row in results.sort_values("date").itertuples(index=False):
            home, away = row.home_team, row.away_team
            hs, as_ = row.home_score, row.away_score
            we_home = self.expected(home, away, row.neutral)

            if hs > as_:
                w_home = 1.0
            elif hs < as_:
                w_home = 0.0
            else:
                w_home = 0.5

            k = _k_for(row.tournament) * _goal_diff_multiplier(hs - as_)
            delta = k * (w_home - we_home)
            self.ratings[home] += delta
            self.ratings[away] -= delta
            self.last_played[home] = row.date
            self.last_played[away] = row.date
        return self

    def rating(self, team: str) -> float:
        return self.ratings[team]

    def win_draw_loss(self, home: str, away: str, neutral: bool) -> tuple[float, float, float]:
        """Convert Elo expectancy into 1X2 probabilities.

        Elo gives an expected *score* (win + half-draw). We split it into
        win/draw/loss using an empirically-calibrated draw model where the
        draw probability peaks when the two sides are evenly matched.
        """
        we = self.expected(home, away, neutral)
        # Draw likelihood is highest at parity, lowest for mismatches.
        draw = 0.30 * (1.0 - 2.0 * abs(we - 0.5))
        draw = max(0.10, min(0.32, draw))
        win = we - draw / 2.0
        loss = 1.0 - we - draw / 2.0
        # numerical guard
        win, loss = max(win, 0.001), max(loss, 0.001)
        total = win + draw + loss
        return win / total, draw / total, loss / total

    def ranking(self, top: int | None = None) -> list[tuple[str, float]]:
        ordered = sorted(self.ratings.items(), key=lambda kv: kv[1], reverse=True)
        return ordered[:top] if top else ordered
