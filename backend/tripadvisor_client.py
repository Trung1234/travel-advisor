from __future__ import annotations

from dataclasses import dataclass

import httpx

from .config import settings


@dataclass(slots=True)
class TripAdvisorPlace:
    name: str
    category: str = "unknown"
    address: str | None = None
    rating: float | None = None
    review_count: int | None = None
    url: str | None = None


class TripAdvisorClientError(RuntimeError):
    pass


class TripAdvisorClient:
    def __init__(self) -> None:
        self.api_key = settings.tripadvisor_api_key
        self.base_url = (settings.tripadvisor_base_url or "").rstrip("/")
        self.endpoint = settings.tripadvisor_endpoint
        self.limit = settings.tripadvisor_limit

    def enabled(self) -> bool:
        return bool(self.api_key and self.base_url)

    def search_places(self, query: str, category: str | None = None) -> list[TripAdvisorPlace]:
        if not self.enabled():
            return []

        params = {"key": self.api_key, "searchQuery": query, "category": category or ""}
        headers = {"Accept": "application/json"}
        url = f"{self.base_url}{self.endpoint}"

        try:
            response = httpx.get(url, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TripAdvisorClientError(f"TripAdvisor request failed: {exc}") from exc

        items = payload.get("data") or payload.get("results") or []
        places: list[TripAdvisorPlace] = []
        for item in items[: self.limit]:
            places.append(
                TripAdvisorPlace(
                    name=str(item.get("name") or item.get("title") or "Unknown place"),
                    category=str(item.get("category") or item.get("type") or category or "unknown"),
                    address=item.get("address"),
                    rating=_to_float(item.get("rating")),
                    review_count=_to_int(item.get("num_reviews") or item.get("reviewCount")),
                    url=item.get("web_url") or item.get("url"),
                )
            )
        return places


def _to_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


_client = TripAdvisorClient()


def get_tripadvisor_places(query: str, category: str | None = None) -> list[TripAdvisorPlace]:
    return _client.search_places(query=query, category=category)
