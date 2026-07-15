"""Thin async client for the Foreca Weather API on RapidAPI.

Only the endpoints the integration needs are implemented:
    /location/search/{query}
    /location/{id}
    /current/{id}
    /forecast/daily/{id}
    /forecast/hourly/{id}

The client keeps no state beyond the API key and session; the coordinator owns
polling cadence and quota accounting.
"""

from __future__ import annotations

from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    API_HOST,
    HEADER_LIMIT,
    HEADER_REMAINING,
    LOGGER,
)


class ForecaApiError(Exception):
    """Raised for non-auth, non-rate-limit API failures."""


class ForecaAuthError(ForecaApiError):
    """Raised when the API key is rejected (HTTP 401/403)."""


class ForecaRateLimitError(ForecaApiError):
    """Raised when the daily/qps quota is exceeded (HTTP 429)."""


class ForecaApiClient:
    """Minimal Foreca RapidAPI client."""

    def __init__(self, api_key: str, session: aiohttp.ClientSession) -> None:
        """Initialize with a RapidAPI key and a shared aiohttp session."""
        self._api_key = api_key
        self._session = session

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": API_HOST,
        }

    async def _get(self, path: str) -> dict[str, Any]:
        """Perform a GET and return the decoded JSON body.

        Raises ForecaAuthError, ForecaRateLimitError, or ForecaApiError with
        context so callers can translate to the right HA outcome.
        """
        url = f"{API_BASE_URL}{path}"
        try:
            async with self._session.get(url, headers=self._headers) as resp:
                # Surface remaining quota for observability. RapidAPI sends this
                # on every response; missing header just means we skip the log.
                remaining = resp.headers.get(HEADER_REMAINING)
                limit = resp.headers.get(HEADER_LIMIT)
                if remaining is not None:
                    LOGGER.debug(
                        "Foreca %s -> HTTP %s (quota %s/%s remaining)",
                        path,
                        resp.status,
                        remaining,
                        limit,
                    )

                if resp.status in (401, 403):
                    raise ForecaAuthError(
                        f"Authentication failed for {path} (HTTP {resp.status})"
                    )
                if resp.status == 429:
                    raise ForecaRateLimitError(
                        f"Rate limit exceeded for {path} (HTTP 429, "
                        f"{remaining} remaining)"
                    )
                if resp.status != 200:
                    body = await resp.text()
                    raise ForecaApiError(
                        f"Unexpected HTTP {resp.status} for {path}: {body[:200]}"
                    )

                return await resp.json()
        except aiohttp.ClientError as err:
            raise ForecaApiError(f"Network error for {path}: {err}") from err

    async def search_locations(self, query: str) -> list[dict[str, Any]]:
        """Search locations by free-text query; returns the raw location list."""
        data = await self._get(f"/location/search/{query}")
        return data.get("locations", [])

    async def get_location(self, location_id: str | int) -> dict[str, Any]:
        """Fetch metadata for a single location id."""
        return await self._get(f"/location/{location_id}")

    async def get_current(self, location_id: str | int) -> dict[str, Any]:
        """Fetch current conditions; returns the inner 'current' object."""
        data = await self._get(f"/current/{location_id}")
        return data.get("current", {})

    async def get_daily_forecast(
        self, location_id: str | int
    ) -> list[dict[str, Any]]:
        """Fetch the daily forecast list."""
        data = await self._get(f"/forecast/daily/{location_id}")
        return data.get("forecast", [])

    async def get_hourly_forecast(
        self, location_id: str | int
    ) -> list[dict[str, Any]]:
        """Fetch the hourly forecast list."""
        data = await self._get(f"/forecast/hourly/{location_id}")
        return data.get("forecast", [])
