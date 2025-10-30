"""Calendar platform for Svitlo Yeah integration."""

import datetime
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator.dtek import DtekCoordinator
from .coordinator.yasno import YasnoCoordinator
from .entity import IntegrationEntity

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Svitlo Yeah calendar platform."""
    LOGGER.debug("Setup new entry: %s", config_entry)
    coordinator: YasnoCoordinator | DtekCoordinator = config_entry.runtime_data
    async_add_entities([PlannedOutagesCalendar(coordinator)])


class PlannedOutagesCalendar(IntegrationEntity, CalendarEntity):
    """Implementation of the Planned Outages Calendar entity."""

    def __init__(
        self,
        coordinator: YasnoCoordinator | DtekCoordinator,
    ) -> None:
        """Initialize the Planned Outages Calendar entity."""
        super().__init__(coordinator)
        self.entity_id = (
            f"calendar.planned_outages"
            f"_{coordinator.region_name}"
            f"_{coordinator.provider_name}"
            f"_{coordinator.group}"
        )
        self.entity_description = EntityDescription(
            key="calendar",
            name="Calendar",
            translation_key="calendar",
        )
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}-"
            f"{coordinator.group}-"
            f"{self.entity_description.key}"
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event or None."""
        return self.coordinator.get_current_event()

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        LOGGER.debug("Get events between %s and %s", start_date, end_date)
        return self.coordinator.get_events_between(start_date, end_date)
