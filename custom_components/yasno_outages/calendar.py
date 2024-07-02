"""Calendar platform for Yasno outages integration."""

import datetime
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_utils

from .const import ATTR_GROUP, DOMAIN, TRANSLATION_KEY_CALENDAR
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
            name=f"Yasno Outages Group {coordinator.group}",
            translation_key=TRANSLATION_KEY_CALENDAR,
        )
        self._attr_unique_id = (
            f"{config_entry.domain}_{config_entry.entry_id}_{coordinator.group}"
        )
        self._config_entry = config_entry

        LOGGER.debug("Initiated with entry data: %s", self._config_entry.data)
        LOGGER.debug("Initiated with entry options: %s", self._config_entry.options)

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"Yasno Outages Group {self.coordinator.group}"

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
        current_event = self.coordinator.data.at(now)
        LOGGER.debug("Current event for %s is: %s", now, current_event)
        if current_event:
            return self._transform_event(current_event[0])
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events = self.coordinator.data.between(start_date, end_date)
        return [self._transform_event(event) for event in events]

    def _transform_event(self, event: dict | None) -> CalendarEvent:
        """Transform an event into a CalendarEvent."""
        return CalendarEvent(
            summary=event.get("SUMMARY"),
            start=event.decoded("DTSTART"),
            end=event.decoded("DTEND"),
        )
