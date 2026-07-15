"""Sensor platform for Foreca.

These sensors expose current-conditions values as standalone entities (with
their own history graphs and device classes) alongside the weather entity.
They read from the same coordinator, so they add no API calls.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ForecaConfigEntry
from .const import (
    ATTRIBUTION,
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import ForecaDataUpdateCoordinator

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class ForecaSensorEntityDescription(SensorEntityDescription):
    """Describes a Foreca sensor and how to read it from current conditions."""

    value_fn: Callable[[dict[str, Any]], float | None]


SENSOR_TYPES: tuple[ForecaSensorEntityDescription, ...] = (
    ForecaSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda current: current.get("temperature"),
    ),
    ForecaSensorEntityDescription(
        key="uv_index",
        translation_key="uv_index",
        # No dedicated device class for UV index; report as a plain measurement.
        native_unit_of_measurement="UV index",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda current: current.get("uvIndex"),
    ),
)


async def async_setup_entry(
    hass,
    entry: ForecaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Foreca sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        ForecaSensor(coordinator, entry, description)
        for description in SENSOR_TYPES
    )


class ForecaSensor(
    CoordinatorEntity[ForecaDataUpdateCoordinator], SensorEntity
):
    """A single Foreca current-conditions sensor."""

    entity_description: ForecaSensorEntityDescription
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ForecaDataUpdateCoordinator,
        entry: ForecaConfigEntry,
        description: ForecaSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        location_id = entry.data[CONF_LOCATION_ID]
        self._attr_unique_id = f"{location_id}_{description.key}"
        # Share the weather entity's device so they group together.
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(location_id))},
            "manufacturer": MANUFACTURER,
            "name": entry.data.get(CONF_LOCATION_NAME, "Foreca"),
        }

    @property
    def native_value(self) -> float | None:
        """Return the sensor value from the latest current conditions."""
        return self.entity_description.value_fn(self.coordinator.data.current)
