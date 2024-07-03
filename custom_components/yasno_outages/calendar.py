"""Calendar platform for Yasno outages integration."""

import datetime
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_utils

from .const import ATTR_GROUP, DOMAIN
from .coordinator import YasnoOutagesCoordinator

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Yasno outages calendar platform."""
    LOGGER.debug("Setup new entry: %s", config_entry)
    coordinator: YasnoOutagesCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([YasnoOutagesCalendar(coordinator, config_entry)])


class YasnoOutagesCalendar(CoordinatorEntity[YasnoOutagesCoordinator], CalendarEntity):
    """Implementation of calendar entity."""

    def __init__(
        self,
        coordinator: YasnoOutagesCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the YasnoOutagesCalendar entity."""
        super().__init__(coordinator)
        self.entity_description = EntityDescription(
            key=DOMAIN,
            # TODO(denysdovhan): Find a way to translated entity's name
            name=f"Yasno Group {coordinator.group} Calendar",
            translation_key="outages_calendar",
        )
        self._attr_unique_id = (
            f"{config_entry.domain}_{config_entry.entry_id}_{coordinator.group}"
        )
        self._config_entry = config_entry

        LOGGER.debug("Initiated with entry data: %s", self._config_entry.data)
        LOGGER.debug("Initiated with entry options: %s", self._config_entry.options)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        return DeviceInfo(
            name=f"Yasno Group {self.coordinator.group}",
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return the extra state attributes."""
        return {
            ATTR_GROUP: self.coordinator.group,
        }

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event or None."""
        now = dt_utils.now()
        LOGGER.debug("Getting current event for %s", now)
        return self.coordinator.get_current_event(now)

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        LOGGER.debug('Getting all events between "%s" -> "%s"', start_date, end_date)
        return self.coordinator.get_events(start_date, end_date)
