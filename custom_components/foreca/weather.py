"""Weather platform for Foreca."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_APPARENT_TEMP,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ForecaConfigEntry
from .const import (
    ATTRIBUTION,
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import ForecaDataUpdateCoordinator

# Only one entity per config entry and the coordinator serializes fetches, so
# no parallelism is needed (also keeps us clear of the 5 qps ceiling).
PARALLEL_UPDATES = 0

# Foreca symbol codes are "[d|n]NNN". The leading digit of the numeric part
# encodes the sky/precip family; we map that family to an HA condition. Day vs
# night ('d'/'n') only affects sunny -> clear-night. See Foreca symbol legend.
_SYMBOL_FAMILY_TO_CONDITION = {
    "0": "sunny",  # clear / mostly clear
    "1": "partlycloudy",  # partly cloudy
    "2": "cloudy",  # cloudy
    "3": "cloudy",  # overcast
    "4": "rainy",  # rain / showers
    "5": "snowy",  # snow
    "6": "snowy-rainy",  # sleet / mixed
    "7": "lightning-rainy",  # thunderstorms
    "8": "fog",  # fog / mist
}


def _map_condition(symbol: str | None) -> str | None:
    """Translate a Foreca symbol code to an HA condition string."""
    if not symbol or len(symbol) < 2:
        return None
    is_night = symbol[0] == "n"
    family = symbol[1]
    condition = _SYMBOL_FAMILY_TO_CONDITION.get(family)
    if condition == "sunny" and is_night:
        return "clear-night"
    return condition


async def async_setup_entry(
    hass,
    entry: ForecaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Foreca weather entity from a config entry."""
    async_add_entities([ForecaWeatherEntity(entry.runtime_data, entry)])


class ForecaWeatherEntity(
    SingleCoordinatorWeatherEntity[ForecaDataUpdateCoordinator]
):
    """A Foreca-backed weather entity."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_precipitation_unit = UnitOfLength.MILLIMETERS
    _attr_native_visibility_unit = UnitOfLength.METERS
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(
        self,
        coordinator: ForecaDataUpdateCoordinator,
        entry: ForecaConfigEntry,
    ) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        location_id = entry.data[CONF_LOCATION_ID]
        self._attr_unique_id = str(location_id)
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, str(location_id))},
            manufacturer=MANUFACTURER,
            name=entry.data.get(CONF_LOCATION_NAME, "Foreca"),
        )

    @property
    def _current(self) -> dict[str, Any]:
        return self.coordinator.data.current

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        return _map_condition(self._current.get("symbol"))

    @property
    def native_temperature(self) -> float | None:
        return self._current.get("temperature")

    @property
    def native_apparent_temperature(self) -> float | None:
        return self._current.get("feelsLikeTemp")

    @property
    def native_dew_point(self) -> float | None:
        return self._current.get("dewPoint")

    @property
    def humidity(self) -> float | None:
        return self._current.get("relHumidity")

    @property
    def native_pressure(self) -> float | None:
        return self._current.get("pressure")

    @property
    def native_wind_speed(self) -> float | None:
        return self._current.get("windSpeed")

    @property
    def native_wind_gust_speed(self) -> float | None:
        return self._current.get("windGust")

    @property
    def wind_bearing(self) -> float | None:
        return self._current.get("windDir")

    @property
    def native_visibility(self) -> float | None:
        return self._current.get("visibility")

    @property
    def cloud_coverage(self) -> float | None:
        return self._current.get("cloudiness")

    @property
    def uv_index(self) -> float | None:
        return self._current.get("uvIndex")

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        return [
            {
                ATTR_FORECAST_TIME: day.get("date"),
                ATTR_FORECAST_CONDITION: _map_condition(day.get("symbol")),
                ATTR_FORECAST_NATIVE_TEMP: day.get("maxTemp"),
                ATTR_FORECAST_NATIVE_TEMP_LOW: day.get("minTemp"),
                ATTR_FORECAST_NATIVE_PRECIPITATION: day.get("precipAccum"),
                ATTR_FORECAST_NATIVE_WIND_SPEED: day.get("maxWindSpeed"),
                ATTR_FORECAST_WIND_BEARING: day.get("windDir"),
            }
            for day in self.coordinator.data.daily
        ]

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""
        return [
            {
                ATTR_FORECAST_TIME: hour.get("time"),
                ATTR_FORECAST_CONDITION: _map_condition(hour.get("symbol")),
                ATTR_FORECAST_NATIVE_TEMP: hour.get("temperature"),
                ATTR_FORECAST_NATIVE_APPARENT_TEMP: hour.get("feelsLikeTemp"),
                ATTR_FORECAST_NATIVE_PRECIPITATION: hour.get("precipAccum"),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: hour.get("precipProb"),
                ATTR_FORECAST_NATIVE_WIND_SPEED: hour.get("windSpeed"),
                ATTR_FORECAST_WIND_BEARING: hour.get("windDir"),
            }
            for hour in self.coordinator.data.hourly
        ]
