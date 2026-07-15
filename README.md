# Foreca Weather for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration that
provides current conditions and hourly/daily forecasts from
[Foreca](https://www.foreca.com/), accessed through the
[Foreca Weather API on RapidAPI](https://rapidapi.com/foreca-ltd-foreca-ltd-default/api/foreca-weather).

This integration talks to Foreca **via RapidAPI**, not the direct Foreca
enterprise API. You supply your own RapidAPI key; the integration is designed
to stay comfortably within the free **Basic** plan's limits (1000 requests/day,
5 requests/second).

## Features

- Current conditions: temperature, apparent temperature, dew point, humidity,
  pressure, wind speed/gust/bearing, visibility, cloud coverage, and UV index.
- Daily forecast (7 days) and hourly forecast (24 hours) via Home Assistant's
  weather forecast subscription model.
- UI configuration (config flow) — no YAML required.
- Search for your location by name and pick from matching results.
- Multiple locations supported: add the integration once per location. All
  entries can share a single RapidAPI key.

## Getting a RapidAPI key

The integration authenticates to Foreca through RapidAPI, so you need a RapidAPI
account and a subscription to the Foreca Weather API.

1. Create a free account at [rapidapi.com](https://rapidapi.com/) (or sign in).
2. Open the
   [Foreca Weather API](https://rapidapi.com/foreca-ltd-foreca-ltd-default/api/foreca-weather)
   listing.
3. Click **Subscribe to Test** and choose the **Basic** plan. It is free and
   includes 1000 requests per day at up to 5 requests per second. (Paid plans
   with higher limits also work; this integration does not require them.)
4. After subscribing, open the **Endpoints** tab and find your key under the
   `X-RapidAPI-Key` header in the code snippet on the right. Copy that value —
   it is what you'll paste into Home Assistant.

Your key is stored in Home Assistant's config entry, not in this integration's
code. Treat it like a password; anyone with it can consume your quota.

## Installation

### HACS (recommended)

1. In HACS, add this repository as a custom repository (category: *Integration*):
   `https://github.com/mr-ransel/ha-foreca-weather`
2. Install **Foreca** from HACS.
3. Restart Home Assistant.

### Manual

1. Copy the `custom_components/foreca` directory into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration** and search for
   **Foreca**.
2. Enter your **RapidAPI key** and a **location search** term (e.g. a city
   name).
3. Pick the matching location from the list of results.

To add more locations, add the integration again — reuse the same API key.

## How it handles rate limits

The Foreca Basic plan allows 1000 requests per day. A single data update
coordinator per location polls on a base interval and fetches each endpoint on
its own cadence, so faster-changing data updates more often without wasting
quota on slow-changing forecasts:

| Data              | Interval | Requests/day/location |
| ----------------- | -------- | --------------------- |
| Current conditions | 15 min   | 96                    |
| Hourly forecast   | 45 min   | 32                    |
| Daily forecast    | 3 hours  | 8                     |
| **Total**         |          | **~136**              |

That leaves room for several locations on one key plus Home Assistant restarts
(each restart triggers a refresh). For example, four locations use roughly
544 requests/day — still under the 1000/day cap.

The integration reads the RapidAPI rate-limit response headers
(`x-ratelimit-requests-remaining`) and logs the remaining quota at debug level.
If the quota is exceeded (HTTP 429), the coordinator surfaces it as a temporary
update failure and retries on its normal backoff schedule.

## Units

Foreca returns metric units, which the integration reports natively; Home
Assistant converts them to your configured unit system for display:

- Temperature: °C
- Wind speed: m/s
- Pressure: hPa
- Precipitation: mm
- Visibility: m

## Attribution

Weather data provided by Foreca. This project is not affiliated with or endorsed
by Foreca Ltd.
