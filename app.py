"""
app.py
FastAPI entry-point for the AI Travel Planner.

Run with:
    uvicorn app:app --reload
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "planner"))

from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kg_builder import TravelKG
from recommender import TravelRecommender
from itinerary_generator import ItineraryGenerator

# --------------------------------------------------------------------------- #
# App & shared state
# --------------------------------------------------------------------------- #
app = FastAPI(title="AI Travel Planner", version="0.2.0")

_kg: Optional[TravelKG] = None


def get_kg() -> TravelKG:
    global _kg
    if _kg is None:
        _kg = TravelKG()
        try:
            _kg.load()
        except FileNotFoundError:
            _kg.build()
            _kg.save()
    return _kg


# --------------------------------------------------------------------------- #
# Request / response schemas
# --------------------------------------------------------------------------- #
class RecommendRequest(BaseModel):
    activities: list[str]
    cuisine: Optional[str] = None
    max_daily_budget_eur: Optional[int] = None


class ItineraryRequest(BaseModel):
    city: str
    days: int
    start_date: Optional[date] = None
    budget_per_day_eur: Optional[int] = None
    preferences: Optional[list[str]] = None
    dietary: Optional[str] = None
    use_llm: bool = False


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/recommend")
def recommend(req: RecommendRequest):
    """Return ranked destination recommendations."""
    rec = TravelRecommender(kg=get_kg())
    results = rec.recommend(
        activities=req.activities,
        cuisine=req.cuisine,
        max_daily_budget_eur=req.max_daily_budget_eur,
    )
    if not results:
        raise HTTPException(status_code=404, detail="No matching destinations found.")
    return {"recommendations": results}


@app.post("/itinerary")
def itinerary(req: ItineraryRequest):
    """Generate a day-by-day itinerary for a city."""
    gen = ItineraryGenerator(kg=get_kg(), use_llm=req.use_llm)
    plan = gen.generate(
        city=req.city,
        days=req.days,
        start_date=req.start_date,
        budget_per_day_eur=req.budget_per_day_eur,
        preferences=req.preferences,
        dietary=req.dietary,
    )
    if not plan:
        raise HTTPException(status_code=404, detail=f"City '{req.city}' not found in knowledge graph.")
    return {"itinerary": plan}
