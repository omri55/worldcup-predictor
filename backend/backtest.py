"""Out-of-sample backtest: train on history up to a cutoff, then predict every
international match AFTER the cutoff (matches the model never saw) and measure
1X2 accuracy against simple baselines.

This is the honest test of the *statistical* model (no market odds, since we
have no historical odds feed)."""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/omrifeldman/Desktop/worldcup-predictor/backend")

from app.data.loader import load_datasets
from app.models.dixon_coles import DixonColesModel
from app.models.elo import EloModel
from app.models.predictor import Predictor

CUTOFF = pd.Timestamp("2024-01-01")

ds = load_datasets(force=False)
results = ds.results

train = results[results["date"] < CUTOFF]
test = results[results["date"] >= CUTOFF].copy()
print(f"train matches: {len(train):,} | test matches (unseen): {len(test):,}")
print(f"cutoff: {CUTOFF.date()}  test range: {test['date'].min().date()} -> {test['date'].max().date()}")

elo = EloModel().fit(train)
dc = DixonColesModel().fit(train)
pred = Predictor(dc, elo)


def outcome(hs, as_):
    return "home" if hs > as_ else "away" if hs < as_ else "draw"


n = 0
hit_model = hit_fav = hit_home = 0
brier_model = brier_fav = 0.0

for r in test.itertuples(index=False):
    actual = outcome(r.home_score, r.away_score)
    neutral = bool(r.neutral)

    p = pred.predict(r.home_team, r.away_team, neutral=neutral, market=None)
    probs = {"home": p.prob_home, "draw": p.prob_draw, "away": p.prob_away}
    model_pick = max(probs, key=probs.get)

    # baseline 1: pick the higher-Elo side (favourite); home if neutral tie
    ha = 0.0 if neutral else 65.0
    fav = "home" if elo.rating(r.home_team) + ha >= elo.rating(r.away_team) else "away"

    hit_model += model_pick == actual
    hit_fav += fav == actual
    hit_home += actual == "home"

    # Brier score (lower = better): sum over outcomes of (prob - indicator)^2
    for o in ("home", "draw", "away"):
        ind = 1.0 if actual == o else 0.0
        brier_model += (probs[o] - ind) ** 2
    # favourite as a crude 1-hot for comparison
    fav_probs = {"home": 0.0, "draw": 0.0, "away": 0.0}
    fav_probs[fav] = 1.0
    for o in ("home", "draw", "away"):
        ind = 1.0 if actual == o else 0.0
        brier_fav += (fav_probs[o] - ind) ** 2
    n += 1

print(f"\n=== {n:,} unseen matches ===")
print(f"Model (DC+Elo) accuracy : {hit_model/n*100:5.1f}%")
print(f"Baseline 'favourite'    : {hit_fav/n*100:5.1f}%")
print(f"Baseline 'always home'  : {hit_home/n*100:5.1f}%")
print(f"Random guess (1/3)      :  33.3%")
print(f"\nBrier score (lower better)")
print(f"  Model      : {brier_model/n:.3f}")
print(f"  Favourite  : {brier_fav/n:.3f}")
