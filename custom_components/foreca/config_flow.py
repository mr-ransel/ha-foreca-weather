"""Config flow for the Foreca integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ForecaApiClient,
    ForecaApiError,
    ForecaAuthError,
    ForecaRateLimitError,
)
from .const import (
    CONF_API_KEY,
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    DOMAIN,
)


def _format_location(loc: dict[str, Any]) -> str:
    """Build a human-readable label for a location search result."""
    parts = [loc.get("name")]
    for key in ("state", "country"):
        if value := loc.get(key):
            parts.append(value)
    return ", ".join(p for p in parts if p)


class ForecaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Foreca config flow: API key -> location search -> select."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self._api_key: str | None = None
        self._locations: dict[str, dict[str, Any]] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: collect the API key and a location search query."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = ForecaApiClient(
                user_input[CONF_API_KEY],
                async_get_clientsession(self.hass),
            )
            try:
                locations = await client.search_locations(user_input["query"])
            except ForecaAuthError:
                errors["base"] = "invalid_auth"
            except ForecaRateLimitError:
                errors["base"] = "rate_limited"
            except ForecaApiError:
                errors["base"] = "cannot_connect"
            else:
                if not locations:
                    errors["query"] = "no_results"
                else:
                    self._api_key = user_input[CONF_API_KEY]
                    self._locations = {
                        str(loc["id"]): loc for loc in locations
                    }
                    return await self.async_step_location()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required("query"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: choose among the matched locations."""
        if user_input is not None:
            location_id = user_input[CONF_LOCATION_ID]
            location = self._locations[location_id]

            await self.async_set_unique_id(location_id)
            self._abort_if_unique_id_configured()

            name = _format_location(location)
            return self.async_create_entry(
                title=name,
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_LOCATION_ID: location_id,
                    CONF_LOCATION_NAME: location.get("name", name),
                },
            )

        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCATION_ID): vol.In(
                        {
                            loc_id: _format_location(loc)
                            for loc_id, loc in self._locations.items()
                        }
                    )
                }
            ),
        )
