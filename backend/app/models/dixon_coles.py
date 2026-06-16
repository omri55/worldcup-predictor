"""Dixon-Coles bivariate-Poisson goals model for international football.

Each team i has an attack strength a_i and defence strength d_i. For a match
between home h and away a:

    log(lambda_home) = mu + home_adv + a_h - d_a
    log(lambda_away) = mu          + a_a - d_h

Goals are Poisson, with the Dixon-Coles low-score dependence correction `tau`
(rho parameter) that fixes the under-prediction of 0-0 / 1-1 etc.

Matches are weighted by recency (exponential time decay) so current form
dominates without throwing away history. Home advantage is dropped for matches
played at neutral venues (most World Cup games).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ..config import settings


def _tau(home_goals, away_goals, lam, mu, rho):
    """Dixon-Coles correction for low-scoring correlated outcomes."""
    hg, ag = home_goals, away_goals
    out = np.ones_like(lam, dtype=float)
    out = np.where((hg == 0) & (ag == 0), 1.0 - lam * mu * rho, out)
    out = np.where((hg == 0) & (ag == 1), 1.0 + lam * rho, out)
    out = np.where((hg == 1) & (ag == 0), 1.0 + mu * rho, out)
    out = np.where((hg == 1) & (ag == 1), 1.0 - rho, out)
    return out


class DixonColesModel:
    def __init__(self) -> None:
        self.teams: list[str] = []
        self.attack: dict[str, float] = {}
        self.defence: dict[str, float] = {}
        self.home_adv: float = 0.0
        self.intercept: float = 0.0
        self.rho: float = 0.0
        self.fitted: bool = False

    # ---- training ----------------------------------------------------------
    def _prepare(self, results: pd.DataFrame):
        cutoff = results["date"].max() - pd.Timedelta(days=365 * settings.train_years)
        df = results[results["date"] >= cutoff].copy()

        # recency weights: exp(-ln2 * age / half_life)
        max_date = df["date"].max()
        age_days = (max_date - df["date"]).dt.days.to_numpy(dtype=float)
        half_life = settings.time_decay_half_life_days
        weights = np.power(0.5, age_days / half_life)

        teams = sorted(set(df["home_team"]) | set(df["away_team"]))
        return df, teams, weights

    def fit(self, results: pd.DataFrame) -> "DixonColesModel":
        df, teams, weights = self._prepare(results)
        self.teams = teams
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)

        home_i = df["home_team"].map(idx).to_numpy()
        away_i = df["away_team"].map(idx).to_numpy()
        hg = df["home_score"].to_numpy()
        ag = df["away_score"].to_numpy()
        neutral = df["neutral"].to_numpy()
        w = weights

        # params: [attack(n), defence(n), home_adv, intercept, rho]
        # attack[0] pinned via sum-to-zero constraint handled by centering.
        init = np.concatenate([
            np.zeros(n),          # attack
            np.zeros(n),          # defence
            [0.25],               # home advantage
            [0.0],                # intercept (avg log goals)
            [-0.05],              # rho
        ])

        from scipy.special import gammaln

        def poisson_logpmf(k, lam):
            lam = np.maximum(lam, 1e-9)
            return k * np.log(lam) - lam - gammaln(k + 1)

        def neg_loglik(params):
            atk = params[:n]
            dfc = params[n:2 * n]
            home_adv = params[2 * n]
            intercept = params[2 * n + 1]
            rho = params[2 * n + 2]

            ha = np.where(neutral, 0.0, home_adv)
            log_lam = intercept + ha + atk[home_i] - dfc[away_i]
            log_mu = intercept + atk[away_i] - dfc[home_i]
            lam = np.exp(np.clip(log_lam, -5, 5))
            mu = np.exp(np.clip(log_mu, -5, 5))

            ll = poisson_logpmf(hg, lam) + poisson_logpmf(ag, mu)
            tau = _tau(hg, ag, lam, mu, rho)
            tau = np.maximum(tau, 1e-6)
            ll = ll + np.log(tau)
            return -np.sum(w * ll)

        # sum-to-zero on attack & defence keeps the model identifiable.
        cons = [
            {"type": "eq", "fun": lambda p: np.sum(p[:n])},
            {"type": "eq", "fun": lambda p: np.sum(p[n:2 * n])},
        ]
        bounds = [(-3, 3)] * (2 * n) + [(-0.5, 1.0), (-1.0, 1.5), (-0.2, 0.0)]

        res = minimize(
            neg_loglik, init, method="SLSQP", bounds=bounds, constraints=cons,
            options={"maxiter": 200, "ftol": 1e-6},
        )

        p = res.x
        self.attack = {t: float(p[i]) for t, i in idx.items()}
        self.defence = {t: float(p[n + i]) for t, i in idx.items()}
        self.home_adv = float(p[2 * n])
        self.intercept = float(p[2 * n + 1])
        self.rho = float(p[2 * n + 2])
        self.fitted = True
        return self

    # ---- prediction --------------------------------------------------------
    def _strengths(self, team: str) -> tuple[float, float]:
        """Attack/defence for a team, falling back to a weak-team prior."""
        if team in self.attack:
            return self.attack[team], self.defence[team]
        # Unknown / very minor team: below-average attack, leaky defence.
        return -0.6, -0.6

    def expected_goals(self, home: str, away: str, neutral: bool) -> tuple[float, float]:
        a_h, d_h = self._strengths(home)
        a_a, d_a = self._strengths(away)
        ha = 0.0 if neutral else self.home_adv
        lam = np.exp(self.intercept + ha + a_h - d_a)
        mu = np.exp(self.intercept + a_a - d_h)
        return float(lam), float(mu)

    def score_matrix(self, home: str, away: str, neutral: bool) -> np.ndarray:
        """P(home_goals=i, away_goals=j) matrix with DC correction applied."""
        from scipy.stats import poisson

        lam, mu = self.expected_goals(home, away, neutral)
        m = settings.max_goals + 1
        i = np.arange(m)
        ph = poisson.pmf(i, lam)
        pa = poisson.pmf(i, mu)
        mat = np.outer(ph, pa)

        # apply low-score correction to the 2x2 corner
        rho = self.rho
        mat[0, 0] *= 1.0 - lam * mu * rho
        mat[0, 1] *= 1.0 + lam * rho
        mat[1, 0] *= 1.0 + mu * rho
        mat[1, 1] *= 1.0 - rho
        mat = np.clip(mat, 0, None)
        mat /= mat.sum()
        return mat
