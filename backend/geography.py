"""A shared region registry; title mentions are never confirmed event locations."""
import json
import re
from pathlib import Path

REGISTRY = json.loads((Path(__file__).resolve().parents[1] / "config/regions.json").read_text())
REGIONS = REGISTRY["regions"]
COUNTRIES = {region["code"]: region for region in REGIONS}
CITY_COUNTRIES = {city: region["code"] for region in REGIONS for city in region["cities"]}


def mentioned(term, title):
    if re.search(r"[\u3000-\u9fff]", term):
        return term in title
    return bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", title, re.I))


def title_places(title):
    places = []
    for region in REGIONS:
        cities = [city for city, aliases in region["city_aliases"].items() if any(mentioned(term, title) for term in [city, *aliases])]
        if cities:
            places.extend({"country": region["code"], "city": city, "basis": "title_mention"} for city in cities)
        elif any(mentioned(term, title) for term in [region["label"], *region["aliases"]]):
            places.append({"country": region["code"], "city": None, "basis": "title_mention"})
    return places


def places(record):
    return json.loads(record.get("locations_json") or "[]") or ([{"country": record.get("country"), "city": record.get("city")} ] if record.get("country") else [])


def matches_region(record, country=None, city=None):
    locations = places(record)
    if country == "unknown":
        if locations:
            return False
    elif country and country != "all" and not any(place["country"] == country for place in locations):
        return False
    if city and city not in ("all", "全球"):
        inferred = CITY_COUNTRIES.get(city)
        nationwide = record.get("event_type") in ("cinema_release", "streaming_release")
        if not any(place.get("city") == city or (not place.get("city") and place.get("country") == inferred and (nationwide or place.get("basis") == "source_structured")) for place in locations):
            return False
    return True
