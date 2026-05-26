"""
itinerary_generator.py
Day-by-day itinerary generator backed by the knowledge graph and an optional LLM.

Changes from original:
- Activities are now pulled from the KG for the requested city, not hardcoded
  identical strings repeated for every single day
- start_date is a proper parameter (datetime.now() as the trip start made no sense)
- Budget and preferences feed into the day structure
- Optional LLM enrichment: if an Anthropic API key is available the generator
  produces a richer narrative for each day via the Claude API
- Type annotations and docstrings added throughout
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Optional

# Optional LLM enrichment — gracefully degrades if the SDK is absent or
# no API key is configured.
try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

from kg_builder import TravelKG


class ItineraryGenerator:
    """Generate a day-by-day travel itinerary for a given city."""

    def __init__(self, kg: Optional[TravelKG] = None, use_llm: bool = True):
        if kg is None:
            kg = TravelKG()
            try:
                kg.load()
            except FileNotFoundError:
                kg.build()
                kg.save()
        self.kg = kg
        self.use_llm = use_llm and _ANTHROPIC_AVAILABLE and bool(os.getenv("ANTHROPIC_API_KEY"))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def generate(
        self,
        city: str,
        days: int,
        start_date: Optional[date] = None,
        budget_per_day_eur: Optional[int] = None,
        preferences: Optional[list[str]] = None,
        dietary: Optional[str] = None,
    ) -> list[dict]:
        """
        Generate a day-by-day itinerary.

        Parameters
        ----------
        city:
            Destination city (must exist in the KG).
        days:
            Number of travel days.
        start_date:
            First day of the trip (defaults to today).
        budget_per_day_eur:
            Daily budget in EUR for activity/food selection.
        preferences:
            List of activity preferences, e.g. ["Museum", "Wine"].
        dietary:
            Dietary restriction, e.g. "vegetarian" or "vegan".

        Returns
        -------
        List of day dicts, each containing date, city, activities, notes.
        """
        if start_date is None:
            start_date = date.today()

        attractions = self._fetch_attractions(city)
        activities = self._fetch_activities(city)

        itinerary: list[dict] = []
        for i in range(days):
            current_date = start_date + timedelta(days=i)

            # Rotate through available attractions/activities
            day_attractions = attractions[i % len(attractions)] if attractions else "city exploration"
            day_activity = activities[i % len(activities)] if activities else "sightseeing"

            day: dict = {
                "day": i + 1,
                "date": current_date.isoformat(),
                "city": city,
                "highlight": day_attractions,
                "activity_theme": day_activity,
                "notes": self._day_notes(i, days, dietary, budget_per_day_eur),
            }

            # LLM enrichment: narrative paragraph for this day
            if self.use_llm:
                day["narrative"] = self._llm_narrative(day, preferences, dietary)

            itinerary.append(day)

        return itinerary

    # ------------------------------------------------------------------ #
    # KG helpers
    # ------------------------------------------------------------------ #
    def _fetch_attractions(self, city: str) -> list[str]:
        sparql = f"""
        PREFIX travel: <http://travel.ai/ontology/>
        PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?attraction WHERE {{
            ?c a travel:City ;
               rdfs:label "{city}" ;
               travel:hasAttraction ?attraction .
        }}
        """
        rows = self.kg.query(sparql)
        return [r["attraction"] for r in rows]

    def _fetch_activities(self, city: str) -> list[str]:
        sparql = f"""
        PREFIX travel: <http://travel.ai/ontology/>
        PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?act WHERE {{
            ?c a travel:City ;
               rdfs:label "{city}" ;
               travel:hasActivity ?act .
        }}
        """
        rows = self.kg.query(sparql)
        return [r["act"] for r in rows]

    # ------------------------------------------------------------------ #
    # Plain-text day notes (no LLM required)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _day_notes(
        day_index: int,
        total_days: int,
        dietary: Optional[str],
        budget: Optional[int],
    ) -> str:
        parts = []
        if day_index == 0:
            parts.append("Arrival day — check in, settle, explore the neighbourhood.")
        elif day_index == total_days - 1:
            parts.append("Last day — morning sightseeing, pack, depart.")
        if dietary:
            parts.append(f"Look for {dietary}-friendly restaurants.")
        if budget:
            parts.append(f"Target spend: ~€{budget} for food and activities.")
        return "  ".join(parts) if parts else ""

    # ------------------------------------------------------------------ #
    # Optional LLM narrative
    # ------------------------------------------------------------------ #
    def _llm_narrative(
        self,
        day: dict,
        preferences: Optional[list[str]],
        dietary: Optional[str],
    ) -> str:
        """Call the Anthropic API to generate a short narrative for this day."""
        client = anthropic.Anthropic()
        prefs = ", ".join(preferences) if preferences else "general sightseeing"
        diet_note = f"The traveller eats {dietary}." if dietary else ""
        prompt = (
            f"Write a friendly 2-sentence travel narrative for Day {day['day']} of a trip to {day['city']}. "
            f"The highlight is {day['highlight']} and the activity theme is {day['activity_theme']}. "
            f"Traveller interests: {prefs}. {diet_note} "
            f"Keep it concise and inspiring."
        )
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()


# --------------------------------------------------------------------------- #
# Quick smoke-test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    gen = ItineraryGenerator(use_llm=False)   # set use_llm=True if ANTHROPIC_API_KEY is set
    trip = gen.generate(
        city="Paris",
        days=4,
        start_date=date(2025, 6, 1),
        budget_per_day_eur=180,
        preferences=["Museum", "Wine"],
        dietary="vegetarian",
    )
    for day in trip:
        print(f"\n--- Day {day['day']}  ({day['date']}) ---")
        print(f"  Highlight : {day['highlight']}")
        print(f"  Theme     : {day['activity_theme']}")
        print(f"  Notes     : {day['notes']}")
