"""FastAPI application for the World Cup 2026 predictor."""
from __future__ import annotations

from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .engine import engine

scheduler = BackgroundScheduler(daemon=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initial train on startup.
    engine.refresh(force=False)
    # Periodic refresh keeps data + model current throughout the tournament.
    scheduler.add_job(
        lambda: engine.refresh(force=True),
        "interval",
        hours=settings.refresh_interval_hours,
        id="refresh",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="World Cup 2026 Predictor",
    description="Free, always-updated match predictions (Dixon-Coles + Elo).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
def status():
    return engine.status()


@app.post("/api/refresh")
def refresh():
    engine.refresh(force=True)
    return engine.status()


@app.get("/api/teams")
def teams():
    return {"teams": engine.teams()}


@app.get("/api/ranking")
def ranking(top: int = Query(50, ge=1, le=300)):
    return {"ranking": engine.ranking(top)}


@app.get("/api/worldcup/upcoming")
def worldcup_upcoming(year: int = 2026):
    return {
        "year": year,
        "matches": engine.upcoming_world_cup(year),
        "awaiting_result": engine.awaiting_world_cup(year),
    }


@app.get("/api/worldcup/played")
def worldcup_played(year: int = 2026):
    matches = engine.played_world_cup(year)
    hits = sum(1 for m in matches if m.get("prediction_hit"))
    accuracy = round(hits / len(matches), 3) if matches else None
    return {
        "year": year,
        "matches": matches,
        "model_accuracy_so_far": accuracy,
        "hits": hits,
        "total": len(matches),
    }


@app.get("/api/worldcup/simulation")
def worldcup_simulation(n: int = Query(4000, ge=500, le=20000)):
    """Monte-Carlo simulation: advancement & title probabilities per team."""
    return engine.simulate(n)


@app.get("/api/predict")
def predict(
    home: str = Query(..., description="Home team name"),
    away: str = Query(..., description="Away team name"),
    neutral: bool = Query(True, description="Neutral venue (most WC games)"),
    stage: str = Query("group", description="group|r32|r16|qf|sf|third|final"),
):
    teams = set(engine.teams())
    if home not in teams or away not in teams:
        raise HTTPException(
            status_code=404,
            detail="Unknown team. Use /api/teams for valid names.",
        )
    pred = engine.predict_match(home, away, neutral, stage)
    from .engine import _pred_dict

    return {
        "home_team": home,
        "away_team": away,
        "neutral": neutral,
        "stage": stage,
        "prediction": _pred_dict(pred),
    }


@app.get("/")
def root():
    return {
        "name": "World Cup 2026 Predictor API",
        "docs": "/docs",
        "endpoints": [
            "/api/status",
            "/api/teams",
            "/api/ranking",
            "/api/worldcup/upcoming",
            "/api/worldcup/played",
            "/api/predict?home=Brazil&away=Argentina",
        ],
    }
