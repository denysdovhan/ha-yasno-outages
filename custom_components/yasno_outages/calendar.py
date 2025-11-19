"""Calendar platform for Yasno outages integration."""

import datetime
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_utils

from .api import OutageEvent
from .api.models import OutageSource
from .coordinator import YasnoOutagesCoordinator
from .data import YasnoOutagesConfigEntry
from .entity import YasnoOutagesEntity

LOGGER = logging.getLogger(__name__)


def to_calendar_event(
    coordinator: YasnoOutagesCoordinator,
    event: OutageEvent,
) -> CalendarEvent:
    """Convert OutageEvent into Home Assistant CalendarEvent."""
    source = event.source or OutageSource.PLANNED
    summary = coordinator.event_summary_map.get(source, "Outage")
    calendar_event = CalendarEvent(
        summary=summary,
        start=event.start,
        end=event.end,
        description=event.event_type.value,
        uid=f"{source.value}-{event.start.isoformat()}",
    )
    LOGGER.debug("Calendar Event: %s", calendar_event)
    return calendar_event


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
            YasnoPlannedOutagesCalendar(coordinator),
            YasnoProbableOutagesCalendar(coordinator),
        ]
    )


class YasnoPlannedOutagesCalendar(YasnoOutagesEntity, CalendarEntity):
    """Implementation of planned outages calendar entity."""

    def __init__(
        self,
        coordinator: YasnoOutagesCoordinator,
    ) -> None:
        """Initialize the YasnoPlannedOutagesCalendar entity."""
        super().__init__(coordinator)
        self.entity_description = EntityDescription(
            key="planned_outages",
            name="Planned Outages",
            translation_key="planned_outages",
        )
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}-"
            f"{coordinator.group}-"
            f"{self.entity_description.key}"
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event or None."""
        LOGGER.debug("Getting planned event at now")
        outage_event = self.coordinator.get_planned_event_at(dt_utils.now())
        if not outage_event:
            return None
        return to_calendar_event(self.coordinator, outage_event)

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        LOGGER.debug(
            'Getting planned events between "%s" -> "%s"', start_date, end_date
        )
        events = self.coordinator.get_planned_events_between(start_date, end_date)
        return [to_calendar_event(self.coordinator, event) for event in events]


class YasnoProbableOutagesCalendar(YasnoOutagesEntity, CalendarEntity):
    """Implementation of probable outages calendar entity."""

    def __init__(
        self,
        coordinator: YasnoOutagesCoordinator,
    ) -> None:
        """Initialize the YasnoProbableOutagesCalendar entity."""
        super().__init__(coordinator)
        self.entity_description = EntityDescription(
            key="probable_outages",
            name="Probable Outages",
            translation_key="probable_outages",
        )
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}-"
            f"{coordinator.group}-"
            f"{self.entity_description.key}"
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming probable event or None."""
        LOGGER.debug("Getting probable event at now")
        outage_event = self.coordinator.get_probable_event_at(dt_utils.now())
        if not outage_event:
            return None
        return to_calendar_event(self.coordinator, outage_event)

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return probable calendar events within a datetime range."""
        LOGGER.debug(
            'Getting probable events between "%s" -> "%s"', start_date, end_date
        )
        events = self.coordinator.get_probable_events_between(start_date, end_date)

        # Filter out probable events on days with planned outages if configured
        if self.coordinator.filter_probable:
            planned_dates = self.coordinator.get_planned_dates()
            LOGGER.debug(
                "Filtering out probable events on planned outage dates: %s",
                planned_dates,
            )
            events = [
                event for event in events if event.start.date() not in planned_dates
            ]

        return [to_calendar_event(self.coordinator, event) for event in events]
