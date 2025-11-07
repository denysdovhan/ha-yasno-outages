"""Calendar platform for Yasno outages integration."""

import datetime
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import YasnoOutagesCoordinator
from .data import YasnoOutagesConfigEntry
from .entity import YasnoOutagesEntity

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: YasnoOutagesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Yasno outages calendar platform."""
    LOGGER.debug("Setup new entry: %s", config_entry)
    coordinator = config_entry.runtime_data.coordinator
    async_add_entities(
        [
            YasnoOutagesPlannedCalendar(coordinator),
            YasnoOutagesProbableCalendar(coordinator),
        ]
    )


class YasnoOutagesPlannedCalendar(YasnoOutagesEntity, CalendarEntity):
    """Implementation of planned outages calendar entity."""

    def __init__(
        self,
        coordinator: YasnoOutagesCoordinator,
    ) -> None:
        """Initialize the YasnoOutagesPlannedCalendar entity."""
        super().__init__(coordinator)
        self.entity_description = EntityDescription(
            key="planned_calendar",
            name="Planned Calendar",
            translation_key="planned_calendar",
        )
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}-"
            f"{coordinator.group}-"
            f"{self.entity_description.key}"
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event or None."""
        LOGGER.debug("Getting current planned event")
        return self.coordinator.get_current_event()

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        LOGGER.debug(
            'Getting all planned events between "%s" -> "%s"',
            start_date,
            end_date,
        )
        return self.coordinator.get_events_between(start_date, end_date)


class YasnoOutagesProbableCalendar(YasnoOutagesEntity, CalendarEntity):
    """Implementation of probable outages calendar entity."""

    def __init__(
        self,
        coordinator: YasnoOutagesCoordinator,
    ) -> None:
        """Initialize the YasnoOutagesProbableCalendar entity."""
        super().__init__(coordinator)
        self.entity_description = EntityDescription(
            key="probable_calendar",
            name="Probable Calendar",
            translation_key="probable_calendar",
        )
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}-"
            f"{coordinator.group}-"
            f"{self.entity_description.key}"
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming probable event or None."""
        LOGGER.debug("Getting current probable event")
        # Get current probable events
        now = datetime.datetime.now(datetime.UTC)
        events = self.coordinator.get_probable_events_between(now, now)
        return events[0] if events else None

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        LOGGER.debug(
            'Getting all probable events between "%s" -> "%s"',
            start_date,
            end_date,
        )
        return self.coordinator.get_probable_events_between(start_date, end_date)
