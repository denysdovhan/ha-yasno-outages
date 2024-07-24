"""Calendar platform for Yasno outages integration."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import STATE_MAYBE, STATE_OFF, STATE_ON
from .coordinator import YasnoOutagesCoordinator
from .entity import YasnoOutagesEntity

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class YasnoOutagesSensorDescription(SensorEntityDescription):
    """Yasno Outages entity description."""

    val_func: Callable[[YasnoOutagesCoordinator], Any]


SENSOR_TYPES: tuple[YasnoOutagesSensorDescription, ...] = (
    YasnoOutagesSensorDescription(
        key="electricity",
        translation_key="electricity",
        icon="mdi:transmission-tower",
        device_class=SensorDeviceClass.ENUM,
        options=[STATE_ON, STATE_OFF, STATE_MAYBE],
        val_func=lambda coordinator: coordinator.current_state,
    ),
    YasnoOutagesSensorDescription(
        key="next_outage",
        translation_key="next_outage",
        icon="mdi:calendar-remove",
        device_class=SensorDeviceClass.TIMESTAMP,
        val_func=lambda coordinator: coordinator.next_outage,
    ),
    YasnoOutagesSensorDescription(
        key="next_possible_outage",
        translation_key="next_possible_outage",
        icon="mdi:calendar-question",
        device_class=SensorDeviceClass.TIMESTAMP,
        val_func=lambda coordinator: coordinator.next_possible_outage,
    ),
    YasnoOutagesSensorDescription(
        key="next_connectivity",
        translation_key="next_connectivity",
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.TIMESTAMP,
        val_func=lambda coordinator: coordinator.next_connectivity,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Yasno outages calendar platform."""
    LOGGER.debug("Setup new entry: %s", config_entry)
    coordinator: YasnoOutagesCoordinator = config_entry.runtime_data
    async_add_entities(
        YasnoOutagesSensor(coordinator, description) for description in SENSOR_TYPES
    )


class YasnoOutagesSensor(YasnoOutagesEntity, SensorEntity):
    """Implementation of connection entity."""

    entity_description: YasnoOutagesSensorDescription

    def __init__(
        self,
        coordinator: YasnoOutagesCoordinator,
        entity_description: YasnoOutagesSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}-"
            f"{coordinator.group}-"
            f"{self.entity_description.key}"
        )

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self.entity_description.val_func(self.coordinator)
