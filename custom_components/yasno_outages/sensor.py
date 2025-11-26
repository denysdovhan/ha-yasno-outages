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
from homeassistant.const import STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_EVENT_END,
    ATTR_EVENT_START,
    ATTR_EVENT_TYPE,
    STATE_NORMAL,
    STATE_OUTAGE,
    STATE_STATUS_EMERGENCY_SHUTDOWNS,
    STATE_STATUS_SCHEDULE_APPLIES,
    STATE_STATUS_WAITING_FOR_SCHEDULE,
)
from .coordinator import YasnoOutagesCoordinator
from .data import YasnoOutagesConfigEntry
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
        options=[STATE_NORMAL, STATE_OUTAGE, STATE_UNKNOWN],
        val_func=lambda coordinator: coordinator.current_state,
    ),
    YasnoOutagesSensorDescription(
        key="next_planned_outage",
        translation_key="next_planned_outage",
        icon="mdi:calendar-remove",
        device_class=SensorDeviceClass.TIMESTAMP,
        val_func=lambda coordinator: coordinator.next_planned_outage,
    ),
    YasnoOutagesSensorDescription(
        key="next_probable_outage",
        translation_key="next_probable_outage",
        icon="mdi:calendar-question",
        device_class=SensorDeviceClass.TIMESTAMP,
        val_func=lambda coordinator: coordinator.next_probable_outage,
    ),
    YasnoOutagesSensorDescription(
        key="next_connectivity",
        translation_key="next_connectivity",
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.TIMESTAMP,
        val_func=lambda coordinator: coordinator.next_connectivity,
    ),
    YasnoOutagesSensorDescription(
        key="schedule_updated_on",
        translation_key="schedule_updated_on",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        val_func=lambda coordinator: coordinator.schedule_updated_on,
    ),
    YasnoOutagesSensorDescription(
        key="status_today",
        translation_key="status_today",
        icon="mdi:calendar-today",
        device_class=SensorDeviceClass.ENUM,
        options=[
            STATE_STATUS_SCHEDULE_APPLIES,
            STATE_STATUS_WAITING_FOR_SCHEDULE,
            STATE_STATUS_EMERGENCY_SHUTDOWNS,
            STATE_UNKNOWN,
        ],
        entity_category=EntityCategory.DIAGNOSTIC,
        val_func=lambda coordinator: coordinator.status_today,
    ),
    YasnoOutagesSensorDescription(
        key="status_tomorrow",
        translation_key="status_tomorrow",
        icon="mdi:calendar",
        device_class=SensorDeviceClass.ENUM,
        options=[
            STATE_STATUS_SCHEDULE_APPLIES,
            STATE_STATUS_WAITING_FOR_SCHEDULE,
            STATE_STATUS_EMERGENCY_SHUTDOWNS,
            STATE_UNKNOWN,
        ],
        entity_category=EntityCategory.DIAGNOSTIC,
        val_func=lambda coordinator: coordinator.status_tomorrow,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: YasnoOutagesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Yasno outages calendar platform."""
    LOGGER.debug("Setup new entry: %s", config_entry)
    coordinator = config_entry.runtime_data.coordinator
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
        event = self.coordinator.current_event
        return {
            ATTR_EVENT_TYPE: event.event_type.value if event else STATE_UNKNOWN,
            ATTR_EVENT_START: event.start.isoformat() if event else None,
            ATTR_EVENT_END: event.end.isoformat() if event else None,
        }
