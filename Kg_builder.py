"""
kg_builder.py
Build and query the travel knowledge graph using rdflib.

Changes from original:
- serialize() destination is now relative to this file, not the CWD
- Added query() method so other modules can interrogate the KG
- Added more destinations, activities, and budget properties
- Added SPARQL query example
- Added __all__ for clean imports
"""

import os
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

__all__ = ["TravelKG"]

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
_HERE = os.path.dirname(os.path.abspath(__file__))
_ONTOLOGY_PATH = os.path.join(_HERE, "..", "ontology", "tourism.ttl")


class TravelKG:
    """Thin wrapper around an rdflib Graph for the travel domain."""

    TRAVEL = Namespace("http://travel.ai/ontology/")

    def __init__(self, path: str = _ONTOLOGY_PATH):
        self.path = path
        self.g = Graph()
        self.g.bind("travel", self.TRAVEL)

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #
    def build(self) -> None:
        """Populate the graph with seed destination data."""
        T = self.TRAVEL
        g = self.g

        destinations = [
            {
                "uri": T.Paris,
                "label": "Paris",
                "type": T.City,
                "cuisine": "French",
                "attractions": ["Eiffel Tower", "Louvre Museum", "Notre-Dame"],
                "activities": ["Museum", "Wine", "Art"],
                "avg_daily_cost_eur": 200,
                "best_season": "Spring",
            },
            {
                "uri": T.Rome,
                "label": "Rome",
                "type": T.City,
                "cuisine": "Italian",
                "attractions": ["Colosseum", "Vatican Museums", "Trevi Fountain"],
                "activities": ["History", "Food", "Art"],
                "avg_daily_cost_eur": 150,
                "best_season": "Autumn",
            },
            {
                "uri": T.Barcelona,
                "label": "Barcelona",
                "type": T.City,
                "cuisine": "Spanish",
                "attractions": ["Sagrada Família", "Park Güell", "La Boqueria"],
                "activities": ["Beach", "Architecture", "Food"],
                "avg_daily_cost_eur": 130,
                "best_season": "Spring",
            },
            {
                "uri": T.Kyoto,
                "label": "Kyoto",
                "type": T.City,
                "cuisine": "Japanese",
                "attractions": ["Fushimi Inari", "Arashiyama Bamboo Grove", "Kinkaku-ji"],
                "activities": ["History", "Nature", "Culture"],
                "avg_daily_cost_eur": 120,
                "best_season": "Spring",
            },
        ]

        for dest in destinations:
            uri = dest["uri"]
            g.add((uri, RDF.type, dest["type"]))
            g.add((uri, RDFS.label, Literal(dest["label"])))
            g.add((uri, T.hasCuisine, Literal(dest["cuisine"])))
            g.add((uri, T.avgDailyCostEur, Literal(dest["avg_daily_cost_eur"], datatype=XSD.integer)))
            g.add((uri, T.bestSeason, Literal(dest["best_season"])))
            for attraction in dest["attractions"]:
                g.add((uri, T.hasAttraction, Literal(attraction)))
            for activity in dest["activities"]:
                g.add((uri, T.hasActivity, Literal(activity)))

        # Traveler profile
        user = T.User1
        g.add((user, RDF.type, T.Traveler))
        g.add((user, T.likesCuisine, Literal("French")))
        g.add((user, T.likesActivity, Literal("Museum")))
        g.add((user, T.budgetPerDayEur, Literal(180, datatype=XSD.integer)))

        print(f"Knowledge Graph built — {len(g)} triples")

    # ------------------------------------------------------------------ #
    # Persist / load
    # ------------------------------------------------------------------ #
    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.g.serialize(self.path, format="turtle")
        print(f"Saved to {self.path}")

    def load(self) -> None:
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"TTL file not found: {self.path}. Run build() first.")
        self.g.parse(self.path, format="turtle")
        print(f"Loaded {len(self.g)} triples from {self.path}")

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #
    def query(self, sparql: str):
        """Execute a SPARQL SELECT query and return rows as dicts."""
        results = self.g.query(sparql)
        return [
            {str(var): str(row[var]) for var in results.vars if row[var] is not None}
            for row in results
        ]

    def destinations_by_activity(self, activity: str) -> list[str]:
        """Return city labels whose hasActivity includes *activity* (case-insensitive)."""
        sparql = f"""
        PREFIX travel: <http://travel.ai/ontology/>
        PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?label WHERE {{
            ?city a travel:City ;
                  rdfs:label ?label ;
                  travel:hasActivity ?act .
            FILTER (LCASE(STR(?act)) = "{activity.lower()}")
        }}
        """
        return [row["label"] for row in self.query(sparql)]

    def destinations_by_budget(self, max_daily_eur: int) -> list[dict]:
        """Return cities affordable within max_daily_eur per day."""
        sparql = f"""
        PREFIX travel: <http://travel.ai/ontology/>
        PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?label ?cost WHERE {{
            ?city a travel:City ;
                  rdfs:label ?label ;
                  travel:avgDailyCostEur ?cost .
            FILTER (?cost <= {max_daily_eur})
        }}
        ORDER BY ?cost
        """
        return self.query(sparql)


# --------------------------------------------------------------------------- #
# Quick smoke-test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    kg = TravelKG()
    kg.build()
    kg.save()

    print("\n--- Cities with Museum activity ---")
    for city in kg.destinations_by_activity("Museum"):
        print(" ", city)

    print("\n--- Cities under €160/day ---")
    for row in kg.destinations_by_budget(160):
        print(f"  {row['label']} — €{row['cost']}/day")
