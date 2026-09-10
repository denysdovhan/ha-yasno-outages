"""Calendar platform for Yasno outages integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import STATE_UNKNOWN, EntityCategory

from .const import (
    ATTR_EVENT_END,
    ATTR_EVENT_START,
    ATTR_EVENT_TYPE,
    ATTR_METER_READING_METHOD,
    ATTR_METER_READING_OWNER,
    LOGIN_MODE_ACCOUNT,
    STATE_NORMAL,
    STATE_OUTAGE,
    STATE_STATUS_EMERGENCY_SHUTDOWNS,
    STATE_STATUS_NO_OUTAGES,
    STATE_STATUS_SCHEDULE_APPLIES,
    STATE_STATUS_WAITING_FOR_SCHEDULE,
)
from .entity import YasnoOutagesEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import YasnoOutagesCoordinator
    from .data import YasnoOutagesConfigEntry

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class YasnoOutagesSensorDescription(SensorEntityDescription):
    """Yasno Outages entity description."""

    val_func: Callable[[YasnoOutagesCoordinator], Any]
    attr_func: Callable[[YasnoOutagesCoordinator], dict[str, Any]] | None = None


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
            STATE_STATUS_NO_OUTAGES,
            STATE_STATUS_SCHEDULE_APPLIES,
            STATE_STATUS_WAITING_FOR_SCHEDULE,
            STATE_STATUS_EMERGENCY_SHUTDOWNS,
            STATE_STATUS_NO_OUTAGES,
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
            STATE_STATUS_NO_OUTAGES,
            STATE_STATUS_SCHEDULE_APPLIES,
            STATE_STATUS_WAITING_FOR_SCHEDULE,
            STATE_STATUS_EMERGENCY_SHUTDOWNS,
            STATE_STATUS_NO_OUTAGES,
            STATE_UNKNOWN,
        ],
        entity_category=EntityCategory.DIAGNOSTIC,
        val_func=lambda coordinator: coordinator.status_tomorrow,
    ),
)

# Sensors only available when the entry is set up with authenticated account login
ACCOUNT_SENSOR_TYPES: tuple[YasnoOutagesSensorDescription, ...] = (
    YasnoOutagesSensorDescription(
        key="account_balance",
        translation_key="account_balance",
        icon="mdi:cash",
        native_unit_of_measurement="UAH",
        suggested_display_precision=2,
        val_func=lambda coordinator: coordinator.account_balance,
    ),
    YasnoOutagesSensorDescription(
        key="account_address",
        translation_key="account_address",
        icon="mdi:map-marker",
        entity_category=EntityCategory.DIAGNOSTIC,
        val_func=lambda coordinator: coordinator.account_address,
    ),
    YasnoOutagesSensorDescription(
        key="account_last_meter_reading_day",
        translation_key="account_last_meter_reading_day",
        icon="mdi:counter",
        state_class="measurement",
        native_unit_of_measurement="kWh",
        val_func=lambda coordinator: coordinator.account_last_meter_reading_day,
        attr_func=lambda coordinator: {
            ATTR_METER_READING_OWNER: coordinator.account_last_meter_reading_owner,
            ATTR_METER_READING_METHOD: coordinator.account_last_meter_reading_method,
        },
    ),
    YasnoOutagesSensorDescription(
        key="account_last_meter_reading_night",
        translation_key="account_last_meter_reading_night",
        icon="mdi:counter",
        state_class="measurement",
        native_unit_of_measurement="kWh",
        val_func=lambda coordinator: coordinator.account_last_meter_reading_night,
        attr_func=lambda coordinator: {
            ATTR_METER_READING_OWNER: coordinator.account_last_meter_reading_owner,
            ATTR_METER_READING_METHOD: coordinator.account_last_meter_reading_method,
        },
    ),
    YasnoOutagesSensorDescription(
        key="account_last_meter_reading_on",
        translation_key="account_last_meter_reading_on",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        val_func=lambda coordinator: coordinator.account_last_meter_reading_on,
    ),
    YasnoOutagesSensorDescription(
        key="tariff_name",
        translation_key="tariff_name",
        icon="mdi:file-document-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        val_func=lambda coordinator: coordinator.tariff_name,
    ),
    YasnoOutagesSensorDescription(
        key="tariff_price_day",
        translation_key="tariff_price_day",
        icon="mdi:cash",
        state_class="measurement",
        native_unit_of_measurement="UAH/kWh",
        suggested_display_precision=2,
        val_func=lambda coordinator: coordinator.tariff_price_day,
    ),
    YasnoOutagesSensorDescription(
        key="tariff_price_night",
        translation_key="tariff_price_night",
        icon="mdi:cash",
        state_class="measurement",
        native_unit_of_measurement="UAH/kWh",
        suggested_display_precision=2,
        val_func=lambda coordinator: coordinator.tariff_price_night,
    ),
    YasnoOutagesSensorDescription(
        key="tariff_distribution_price",
        translation_key="tariff_distribution_price",
        icon="mdi:transmission-tower-export",
        state_class="measurement",
        native_unit_of_measurement="UAH/kWh",
        suggested_display_precision=5,
        entity_category=EntityCategory.DIAGNOSTIC,
        val_func=lambda coordinator: coordinator.tariff_distribution_price,
    ),
    YasnoOutagesSensorDescription(
        key="tariff_transfer_price",
        translation_key="tariff_transfer_price",
        icon="mdi:transmission-tower",
        state_class="measurement",
        native_unit_of_measurement="UAH/kWh",
        suggested_display_precision=4,
        entity_category=EntityCategory.DIAGNOSTIC,
        val_func=lambda coordinator: coordinator.tariff_transfer_price,
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
    descriptions = list(SENSOR_TYPES)
    if coordinator.login_mode == LOGIN_MODE_ACCOUNT:
        descriptions.extend(ACCOUNT_SENSOR_TYPES)
    async_add_entities(
        YasnoOutagesSensor(coordinator, description) for description in descriptions
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
        """Return additional attributes for the sensor, if any are defined."""
        if self.entity_description.key == "electricity":
            # Get the current event to provide additional context
            event = self.coordinator.current_event
            return {
                ATTR_EVENT_TYPE: event.event_type.value if event else STATE_UNKNOWN,
                ATTR_EVENT_START: event.start.isoformat() if event else None,
                ATTR_EVENT_END: event.end.isoformat() if event else None,
            }
        if self.entity_description.attr_func:
            return self.entity_description.attr_func(self.coordinator)
        return None
