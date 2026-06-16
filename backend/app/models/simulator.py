"""Monte-Carlo tournament simulator for the World Cup.

For every simulation we:
  1. Play out the group stage (using REAL results for matches already played,
     and sampling the rest from the Dixon-Coles goal distribution).
  2. Rank each group with the official tiebreakers (points, goal difference,
     goals for) and advance the top two, plus the eight best third-placed teams.
  3. Run a single-elimination knockout among the 32 qualifiers, seeded by Elo.

Aggregating over thousands of runs gives, per team:
  P(advance from group), P(reach R16/QF/SF/final), P(win the cup).

Note: the knockout bracket is Elo-seeded as a principled approximation. Once
the official R32 fixtures appear in the source data they can be wired in
directly to replace the seeding.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .dixon_coles import DixonColesModel
from .elo import EloModel


def derive_groups(wc_matches: pd.DataFrame) -> dict[str, list[str]]:
    """Recover the 12 groups from the round-robin fixture structure.

    Each group is a clique of 4 teams that only play within the group during
    the group stage, so the 'plays-against' graph splits into 12 components.
    """
    adj: dict[str, set[str]] = defaultdict(set)
    for r in wc_matches.itertuples():
        adj[r.home_team].add(r.away_team)
        adj[r.away_team].add(r.home_team)

    seen: set[str] = set()
    components: list[list[str]] = []
    for team in adj:
        if team in seen:
            continue
        stack, comp = [team], []
        while stack:
            t = stack.pop()
            if t in seen:
                continue
            seen.add(t)
            comp.append(t)
            stack.extend(adj[t] - seen)
        components.append(sorted(comp))

    components = [c for c in components if len(c) == 4]
    components.sort(key=lambda c: c[0])
    return {chr(ord("A") + i): c for i, c in enumerate(components)}


def _seed_positions(n: int) -> list[int]:
    """Classic single-elimination bracket seed order (keeps 1 & 2 apart)."""
    order = [0]
    while len(order) < n:
        size = len(order) * 2
        order = [x for o in order for x in (o, size - 1 - o)]
    return order


class TournamentSimulator:
    def __init__(
        self,
        dc: DixonColesModel,
        elo: EloModel,
        wc_matches: pd.DataFrame,
    ) -> None:
        self.dc = dc
        self.elo = elo
        self.groups = derive_groups(wc_matches)

        # Fixed group fixtures, tagging the ones already played with their score.
        self.group_fixtures: dict[str, list[tuple]] = defaultdict(list)
        team_to_group = {
            t: g for g, teams in self.groups.items() for t in teams
        }
        for r in wc_matches.itertuples():
            g = team_to_group.get(r.home_team)
            if g is None:
                continue
            played = pd.notna(r.home_score) and pd.notna(r.away_score)
            self.group_fixtures[g].append(
                (
                    r.home_team,
                    r.away_team,
                    int(r.home_score) if played else None,
                    int(r.away_score) if played else None,
                )
            )

        self._eg_cache: dict[tuple[str, str], tuple[float, float]] = {}

    # ---- helpers -----------------------------------------------------------
    def _eg(self, home: str, away: str) -> tuple[float, float]:
        key = (home, away)
        if key not in self._eg_cache:
            self._eg_cache[key] = self.dc.expected_goals(home, away, neutral=True)
        return self._eg_cache[key]

    def _sim_goals(self, home: str, away: str) -> tuple[int, int]:
        lam, mu = self._eg(home, away)
        return int(np.random.poisson(lam)), int(np.random.poisson(mu))

    def _knockout_winner(self, a: str, b: str) -> str:
        hg, ag = self._sim_goals(a, b)
        if hg > ag:
            return a
        if ag > hg:
            return b
        # shootout: decided by relative strength
        we = self.elo.expected(a, b, neutral=True)
        return a if np.random.random() < we else b

    # ---- one full tournament ----------------------------------------------
    def _run_once(self) -> dict[str, str]:
        """Return team -> furthest stage reached this simulation."""
        reached: dict[str, str] = {}
        thirds = []  # (pts, gd, gf, elo, team, group)
        qualifiers_top2 = []

        for g, teams in self.groups.items():
            pts = dict.fromkeys(teams, 0)
            gf = dict.fromkeys(teams, 0)
            ga = dict.fromkeys(teams, 0)
            for home, away, hs, as_ in self.group_fixtures[g]:
                if hs is None:
                    hs, as_ = self._sim_goals(home, away)
                gf[home] += hs; ga[home] += as_
                gf[away] += as_; ga[away] += hs
                if hs > as_:
                    pts[home] += 3
                elif as_ > hs:
                    pts[away] += 3
                else:
                    pts[home] += 1; pts[away] += 1

            standings = sorted(
                teams,
                key=lambda t: (
                    pts[t], gf[t] - ga[t], gf[t], self.elo.rating(t),
                ),
                reverse=True,
            )
            for t in teams:
                reached[t] = "group"
            qualifiers_top2.extend(standings[:2])
            third = standings[2]
            thirds.append(
                (pts[third], gf[third] - ga[third], gf[third],
                 self.elo.rating(third), third)
            )

        # eight best third-placed teams advance
        thirds.sort(reverse=True)
        best_thirds = [t[4] for t in thirds[:8]]
        qualifiers = qualifiers_top2 + best_thirds
        for t in qualifiers:
            reached[t] = "r32"

        # knockout: Elo-seeded single elimination
        seeded = sorted(qualifiers, key=lambda t: self.elo.rating(t), reverse=True)
        positions = _seed_positions(32)
        bracket = [seeded[p] for p in positions]

        stage_names = ["r16", "qf", "sf", "final", "champion"]
        round_idx = 0
        while len(bracket) > 1:
            winners = []
            for i in range(0, len(bracket), 2):
                w = self._knockout_winner(bracket[i], bracket[i + 1])
                winners.append(w)
                reached[w] = stage_names[round_idx]
            bracket = winners
            round_idx += 1

        return reached

    # ---- aggregate ---------------------------------------------------------
    def run(self, n: int = 4000, seed: int | None = 42) -> dict:
        if seed is not None:
            np.random.seed(seed)

        order = ["group", "r32", "r16", "qf", "sf", "final", "champion"]
        rank = {s: i for i, s in enumerate(order)}
        # cumulative counters: counts["r16"] = reached R16 OR deeper
        counts: dict[str, dict[str, int]] = defaultdict(
            lambda: dict.fromkeys(order, 0)
        )

        for _ in range(n):
            reached = self._run_once()
            for team, stage in reached.items():
                top = rank[stage]
                for s in order[: top + 1]:
                    counts[team][s] += 1

        teams_out = []
        for team, c in counts.items():
            g = next((gid for gid, ts in self.groups.items() if team in ts), None)
            teams_out.append({
                "team": team,
                "group": g,
                "elo": round(self.elo.rating(team), 1),
                "advance": round(c["r32"] / n, 4),
                "reach_r16": round(c["r16"] / n, 4),
                "reach_qf": round(c["qf"] / n, 4),
                "reach_sf": round(c["sf"] / n, 4),
                "reach_final": round(c["final"] / n, 4),
                "win_cup": round(c["champion"] / n, 4),
            })
        teams_out.sort(key=lambda x: x["win_cup"], reverse=True)

        return {
            "simulations": n,
            "groups": self.groups,
            "teams": teams_out,
        }
