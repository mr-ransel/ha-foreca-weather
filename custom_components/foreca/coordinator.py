"""Data update coordinator for Foreca.

A single coordinator per location owns polling. It ticks on the fastest
endpoint cadence (current conditions) and fetches the slower endpoints
(hourly, daily forecast) only when their own timers are due. This keeps one
code path and one entity while giving each endpoint an independent cadence to
stay well under the Foreca RapidAPI daily quota.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    ForecaApiClient,
    ForecaAuthError,
    ForecaApiError,
    ForecaRateLimitError,
)
from .const import (
    CONF_API_KEY,
    CONF_LOCATION_ID,
    DAILY_INTERVAL,
    DOMAIN,
    HOURLY_INTERVAL,
    LOGGER,
    UPDATE_INTERVAL,
)


@dataclass
class ForecaData:
    """Container for the latest data across all endpoints.

    Each field holds the most recent successful fetch. Slower endpoints keep
    their previous value between their (less frequent) refreshes.
    """

    current: dict[str, Any] = field(default_factory=dict)
    daily: list[dict[str, Any]] = field(default_factory=list)
    hourly: list[dict[str, Any]] = field(default_factory=list)


class ForecaDataUpdateCoordinator(DataUpdateCoordinator[ForecaData]):
    """Coordinate polling of the Foreca API for a single location."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator from a config entry."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.data[CONF_LOCATION_ID]}",
            update_interval=UPDATE_INTERVAL,
        )
        self._location_id = entry.data[CONF_LOCATION_ID]
        self.client = ForecaApiClient(
            entry.data[CONF_API_KEY],
            async_get_clientsession(hass),
        )
        # Timestamps of the last successful fetch per slow endpoint; None forces
        # a fetch on the first cycle.
        self._last_hourly: datetime | None = None
        self._last_daily: datetime | None = None

    def _is_due(self, last: datetime | None, interval) -> bool:
        """Return True if an endpoint's cadence has elapsed since last fetch."""
        if last is None:
            return True
        return dt_util.utcnow() - last >= interval

    async def _async_update_data(self) -> ForecaData:
        """Fetch current every tick; fetch forecasts only when their timer is due.

        Carries forward the previous forecast data when it isn't due yet, so the
        entity always has a full picture. Raises UpdateFailed / ConfigEntryAuth
        translations via the exception types so HA handles retry/reauth.
        """
        # Start from the last known data so not-yet-due endpoints persist.
        previous = self.data or ForecaData()
        data = ForecaData(
            current=previous.current,
            daily=previous.daily,
            hourly=previous.hourly,
        )

        try:
            # Current conditions: every tick.
            data.current = await self.client.get_current(self._location_id)

            # Hourly forecast: only when its cadence has elapsed.
            if self._is_due(self._last_hourly, HOURLY_INTERVAL):
                data.hourly = await self.client.get_hourly_forecast(
                    self._location_id
                )
                self._last_hourly = dt_util.utcnow()

            # Daily forecast: only when its cadence has elapsed.
            if self._is_due(self._last_daily, DAILY_INTERVAL):
                data.daily = await self.client.get_daily_forecast(
                    self._location_id
                )
                self._last_daily = dt_util.utcnow()

        except ForecaAuthError as err:
            # Trigger HA's reauth flow rather than an endless retry.
            from homeassistant.exceptions import ConfigEntryAuthFailed

            raise ConfigEntryAuthFailed(str(err)) from err
        except ForecaRateLimitError as err:
            # Standard coordinator backoff; we prevent this via cadence math but
            # surface it clearly if a shared key blows the quota.
            raise UpdateFailed(f"Foreca quota exceeded: {err}") from err
        except ForecaApiError as err:
            raise UpdateFailed(str(err)) from err

        return data
