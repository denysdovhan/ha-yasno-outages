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


def to_all_day_calendar_event(
    coordinator: YasnoOutagesCoordinator,
    date: datetime.date,
    status: str,
) -> CalendarEvent:
    """Convert status into Home Assistant all-day CalendarEvent."""
    summary = coordinator.status_event_summary_map.get(status, status)
    calendar_event = CalendarEvent(
        summary=summary,
        start=date,
        end=date + datetime.timedelta(days=1),
        description=status,
        uid=f"status-{date.isoformat()}",
    )
    LOGGER.debug("All-day event: %s", calendar_event)
    return calendar_event


def merge_consecutive_events(events: list[CalendarEvent]) -> list[CalendarEvent]:
    """Merge consecutive calendar events"""
    if not events:
        return []

    sorted_events = sorted(events, key=lambda e: (e.summary, e.start))

    merged = []
    current_event = sorted_events[0]

    for next_event in sorted_events[1:]:
        if (
            current_event.end == next_event.start
            and current_event.description == next_event.description
            and current_event.summary == next_event.summary
        ):
            current_event = CalendarEvent(
                summary=current_event.summary,
                start=current_event.start,
                end=next_event.end,
                description=current_event.description,
                uid=current_event.uid,
            )
        else:
            merged.append(current_event)
            current_event = next_event

    merged.append(current_event)

    return merged


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

    def get_all_day_status_event(
        self,
        date: datetime.date | None,
        status: str | None,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> CalendarEvent | None:
        """Create a status event for a specific date."""
        if date and status and start_date.date() <= date <= end_date.date():
            return to_all_day_calendar_event(self.coordinator, date, status)
        return None

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
        calendar_events = [
            to_calendar_event(self.coordinator, event) for event in events
        ]

        if self.coordinator.merge_multi_day_events:
            calendar_events = merge_consecutive_events(calendar_events)

        if self.coordinator.status_all_day_events:
            if today_status := self.get_all_day_status_event(
                self.coordinator.today_date,
                self.coordinator.status_today,
                start_date,
                end_date,
            ):
                calendar_events.append(today_status)

            if tomorrow_status := self.get_all_day_status_event(
                self.coordinator.tomorrow_date,
                self.coordinator.status_tomorrow,
                start_date,
                end_date,
            ):
                calendar_events.append(tomorrow_status)

        return calendar_events


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

        if self.coordinator.filter_probable:
            planned_dates = self.coordinator.get_planned_dates()
            if outage_event.start.date() in planned_dates:
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
            events = [
                event for event in events if event.start.date() not in planned_dates
            ]

        calendar_events = [
            to_calendar_event(self.coordinator, event) for event in events
        ]
        
        if self.coordinator.merge_multi_day_events:
            calendar_events = merge_consecutive_events(calendar_events)

        return calendar_events
