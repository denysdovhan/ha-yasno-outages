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

from .const import STATE_OUTAGE
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
        options=[STATE_OUTAGE],
        val_func=lambda coordinator: coordinator.current_state,
    ),
    YasnoOutagesSensorDescription(
        key="schedule_updated_on",
        translation_key="schedule_updated_on",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        val_func=lambda coordinator: coordinator.schedule_updated_on,
    ),
    YasnoOutagesSensorDescription(
        key="next_planned_outage",
        translation_key="next_planned_outage",
        icon="mdi:calendar-remove",
        device_class=SensorDeviceClass.TIMESTAMP,
        val_func=lambda coordinator: coordinator.next_planned_outage,
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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes for the electricity sensor."""
        if self.entity_description.key != "electricity":
            return None

        # Get the current event to provide additional context
        current_event = self.coordinator.get_current_event()

        if not current_event:
            return {
                "event_type": "none",
                "event_start": None,
                "event_end": None,
            }

        # Get the event details from the coordinator
        event_dict = current_event.as_dict()
        event_type = event_dict.get("description", "unknown")  # Original summary
        event_start = event_dict.get("start")
        event_end = event_dict.get("end")

        return {
            "event_type": event_type,
            "event_start": event_start,
            "event_end": event_end,
        }
