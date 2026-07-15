"""Constants for the Foreca integration."""

from __future__ import annotations

from datetime import timedelta
import logging

DOMAIN = "foreca"

LOGGER = logging.getLogger(__package__)

# RapidAPI host for the Foreca Weather API.
API_HOST = "foreca-weather.p.rapidapi.com"
API_BASE_URL = f"https://{API_HOST}"

# Config entry / options keys.
CONF_API_KEY = "api_key"
CONF_LOCATION_ID = "location_id"
CONF_LOCATION_NAME = "location_name"

# Per-endpoint poll cadences. The single coordinator ticks on the shortest of
# these (current) and fetches the slower endpoints only when their own timer is
# due. See coordinator.py for the staggering logic.
#
# Daily request budget per location (Foreca RapidAPI basic plan = 1000/day):
#   current: 1440 / 15  =  96/day
#   hourly:  1440 / 45  =  32/day
#   daily:   1440 / 180 =   8/day
#   total   ~= 136 req/day per location, leaving ample headroom for a few
#   locations sharing one API key plus HA restarts.
CURRENT_INTERVAL = timedelta(minutes=15)
HOURLY_INTERVAL = timedelta(minutes=45)
DAILY_INTERVAL = timedelta(hours=3)

# The coordinator's base tick equals the fastest endpoint cadence.
UPDATE_INTERVAL = CURRENT_INTERVAL

# RapidAPI rate-limit response headers (logged each cycle for visibility).
HEADER_LIMIT = "x-ratelimit-requests-limit"
HEADER_REMAINING = "x-ratelimit-requests-remaining"
HEADER_RESET = "x-ratelimit-requests-reset"

ATTRIBUTION = "Weather data provided by Foreca"
MANUFACTURER = "Foreca"
