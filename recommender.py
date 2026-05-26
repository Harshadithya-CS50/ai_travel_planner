"""
recommender.py
Travel recommendation engine backed by the knowledge graph.

Changes from original:
- Case-insensitive matching (original silently returned [] for 'museum' vs 'Museum')
- Multi-preference support: pass a list of activities, ranked by overlap count
- KG-backed: reads from TravelKG instead of a hardcoded dict
- Budget filtering integrated
- Returns ranked dicts instead of a bare list of strings
"""

from __future__ import annotations
from typing import Optional
from kg_builder import TravelKG


class TravelRecommender:
    """Recommend destinations from the knowledge graph."""

    def __init__(self, kg: Optional[TravelKG] = None):
        if kg is None:
            kg = TravelKG()
            try:
                kg.load()
            except FileNotFoundError:
                # Build fresh if no persisted graph exists yet
                kg.build()
                kg.save()
        self.kg = kg

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def recommend(
        self,
        activities: list[str] | str,
        cuisine: Optional[str] = None,
        max_daily_budget_eur: Optional[int] = None,
    ) -> list[dict]:
        """
        Return a ranked list of destination dicts.

        Parameters
        ----------
        activities:
            One or more preferred activities.  Matching is case-insensitive.
        cuisine:
            Optional preferred cuisine style.
        max_daily_budget_eur:
            If given, exclude destinations above this daily cost.

        Returns
        -------
        List of dicts sorted by match_score descending:
            [{"city": str, "match_score": int, "matched_activities": list,
              "avg_daily_cost_eur": int, "best_season": str}, ...]
        """
        if isinstance(activities, str):
            activities = [activities]

        # Normalise to lower-case for case-insensitive comparison
        wanted_acts = [a.lower() for a in activities]
        wanted_cuisine = cuisine.lower() if cuisine else None

        # Pull all candidate cities from the KG
        sparql = """
        PREFIX travel: <http://travel.ai/ontology/>
        PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?label ?act ?cuisine ?cost ?season WHERE {
            ?city a travel:City ;
                  rdfs:label   ?label ;
                  travel:hasActivity     ?act ;
                  travel:hasCuisine      ?cuisine ;
                  travel:avgDailyCostEur ?cost ;
                  travel:bestSeason      ?season .
        }
        """
        rows = self.kg.query(sparql)

        # Aggregate per city
        city_data: dict[str, dict] = {}
        for row in rows:
            name = row["label"]
            if name not in city_data:
                city_data[name] = {
                    "city": name,
                    "cuisine": row.get("cuisine", ""),
                    "avg_daily_cost_eur": int(row.get("cost", 0)),
                    "best_season": row.get("season", ""),
                    "all_activities": [],
                }
            city_data[name]["all_activities"].append(row["act"].lower())

        # Score and filter
        results = []
        for name, data in city_data.items():
            # Budget filter
            if max_daily_budget_eur and data["avg_daily_cost_eur"] > max_daily_budget_eur:
                continue

            # Cuisine filter
            if wanted_cuisine and data["cuisine"].lower() != wanted_cuisine:
                continue

            matched = [a for a in wanted_acts if a in data["all_activities"]]
            if not matched:
                continue

            results.append({
                "city": name,
                "match_score": len(matched),
                "matched_activities": matched,
                "avg_daily_cost_eur": data["avg_daily_cost_eur"],
                "best_season": data["best_season"],
            })

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results


# --------------------------------------------------------------------------- #
# Quick smoke-test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    rec = TravelRecommender()

    print("=== Multi-activity, no budget cap ===")
    for dest in rec.recommend(activities=["Museum", "Art", "Food"]):
        print(f"  {dest['city']}  score={dest['match_score']}  "
              f"matched={dest['matched_activities']}  "
              f"€{dest['avg_daily_cost_eur']}/day")

    print("\n=== Budget ≤ €140/day ===")
    for dest in rec.recommend(activities=["History", "Food"], max_daily_budget_eur=140):
        print(f"  {dest['city']}  €{dest['avg_daily_cost_eur']}/day")

    print("\n=== Case-insensitivity check (was broken in original) ===")
    same = rec.recommend(activities=["museum"])   # lower-case — previously returned []
    print("  'museum' (lower) →", [d["city"] for d in same])
