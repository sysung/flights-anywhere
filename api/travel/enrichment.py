from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from api.google_flights.entities import load_entities
from api.travel.models import PlacesSignal, TravelFilters, WeatherSignal


@dataclass(frozen=True)
class DestinationProfile:
    name: str
    country: str = "Unknown"
    climates: tuple[str, ...] = ()
    interests: tuple[str, ...] = ()


DESTINATION_PROFILES: dict[str, DestinationProfile] = {
    "BKK": DestinationProfile("Bangkok", "Thailand", ("warm", "tropical", "sunny"), ("temples", "food", "nightlife", "culture")),
    "HND": DestinationProfile("Tokyo", "Japan", ("mild",), ("temples", "food", "culture", "museums")),
    "NRT": DestinationProfile("Tokyo", "Japan", ("mild",), ("temples", "food", "culture", "museums")),
    "KIX": DestinationProfile("Osaka", "Japan", ("mild",), ("temples", "food", "culture")),
    "HNL": DestinationProfile("Honolulu", "United States", ("warm", "tropical", "sunny"), ("beaches", "nature", "family", "romantic")),
    "CUN": DestinationProfile("Cancun", "Mexico", ("warm", "tropical", "sunny"), ("beaches", "nightlife", "budget")),
    "BOB": DestinationProfile("Bora Bora", "French Polynesia", ("warm", "tropical", "sunny"), ("beaches", "luxury", "romantic")),
    "ATH": DestinationProfile("Athens", "Greece", ("warm", "sunny"), ("culture", "museums", "food")),
    "BCN": DestinationProfile("Barcelona", "Spain", ("warm", "sunny", "mild"), ("beaches", "food", "nightlife", "culture")),
    "LAX": DestinationProfile("Los Angeles", "United States", ("warm", "sunny"), ("beaches", "food", "nightlife", "museums")),
    "LAS": DestinationProfile("Las Vegas", "United States", ("warm", "sunny"), ("nightlife", "food", "budget")),
    "SEA": DestinationProfile("Seattle", "United States", ("mild",), ("food", "nature", "museums")),
}


class WeatherProvider:
    def get_weather(self, destination: str, filters: TravelFilters) -> WeatherSignal:
        raise NotImplementedError


class PlacesProvider:
    def get_places(self, destination: str, filters: TravelFilters) -> PlacesSignal:
        raise NotImplementedError


class ProfileWeatherProvider(WeatherProvider):
    def get_weather(self, destination: str, filters: TravelFilters) -> WeatherSignal:
        profile = DESTINATION_PROFILES.get(destination.upper(), DestinationProfile(destination.upper()))
        climates = set(profile.climates)
        sunny_score = 0.85 if "sunny" in climates or "tropical" in climates else 0.45
        warm_score = 0.85 if "warm" in climates or "tropical" in climates else 0.5
        rainy_risk = 0.2 if sunny_score >= 0.8 else 0.5
        if "not_rainy" in filters.climates and rainy_risk <= 0.3:
            summary = "Low rain risk based on the destination profile."
        elif filters.climates:
            matched = sorted(set(filters.climates) & climates)
            summary = f"Matches {', '.join(matched)} weather preferences." if matched else "Weather match is moderate."
        else:
            summary = "Weather profile is available for ranking."
        return WeatherSignal(summary=summary, sunny_score=sunny_score, warm_score=warm_score, rainy_risk=rainy_risk)


class ProfilePlacesProvider(PlacesProvider):
    def get_places(self, destination: str, filters: TravelFilters) -> PlacesSignal:
        profile = DESTINATION_PROFILES.get(destination.upper(), DestinationProfile(destination.upper()))
        interests = set(profile.interests)
        requested = set(filters.vibes)
        matched = sorted(requested & interests)
        score = len(matched) / len(requested) if requested else 0.5
        if matched:
            summary = f"Good fit for {', '.join(matched)}."
        elif requested:
            summary = "Interest match is limited from the current destination profile."
        else:
            summary = "Destination interests are available for ranking."
        return PlacesSignal(summary=summary, matched_interests=matched, score=score)


def destination_name(code: str | None) -> str | None:
    if not code:
        return None
    profile = DESTINATION_PROFILES.get(code.upper())
    if profile:
        return profile.name
    place = cached_entities().get(code.upper())
    return place.name if place and place.name else code.upper()


@lru_cache(maxsize=1)
def cached_entities():
    return load_entities()
