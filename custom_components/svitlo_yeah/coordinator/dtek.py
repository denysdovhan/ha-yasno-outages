"""DTEK Coordinator for Svitlo Yeah integration."""

import datetime
import logging

from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_utils

from ..api.dtek import DtekAPI
from ..const import (
    CONF_GROUP,
    DEBUG,
    DOMAIN,
    REGION_SELECTION_DTEK_KEY,
    TRANSLATION_KEY_EVENT_PLANNED_OUTAGE,
    UPDATE_INTERVAL,
)
from ..models import (
    ConnectivityState,
    PlannedOutageEvent,
    PlannedOutageEventType,
)

LOGGER = logging.getLogger(__name__)

TIMEFRAME_TO_CHECK = datetime.timedelta(hours=24)


class DtekCoordinator(DataUpdateCoordinator):
    """Class to manage fetching DTEK outages data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=datetime.timedelta(minutes=UPDATE_INTERVAL),
        )
        self.hass = hass
        self.config_entry = config_entry
        self.translations = {}

        self.group = config_entry.options.get(
            CONF_GROUP,
            config_entry.data.get(CONF_GROUP),
        )

        if not self.group:
            group_error = "Group configuration is required"
            LOGGER.error(group_error)
            raise ValueError(group_error)

        self.api = DtekAPI(group=self.group)

    @property
    def event_name_map(self) -> dict:
        """Return a mapping of event names to translations."""
        return {
            PlannedOutageEventType.DEFINITE: self.translations.get(
                TRANSLATION_KEY_EVENT_PLANNED_OUTAGE
            ),
        }

    async def _async_update_data(self) -> None:
        """Fetch data from DTEK API."""
        await self.async_fetch_translations()
        await self.api.fetch_data(cache_minutes=UPDATE_INTERVAL)

    async def async_fetch_translations(self) -> None:
        """Fetch translations."""
        self.translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "common",
            [DOMAIN],
        )

    def _get_next_event_of_type(
        self, state_type: ConnectivityState
    ) -> CalendarEvent | None:
        """Get the next event of a specific type."""
        now = dt_utils.now()
        next_events = sorted(
            self.get_events_between(now, now + TIMEFRAME_TO_CHECK),
            key=lambda _: _.start,
        )
        for event in next_events:
            if self._event_to_state(event) == state_type and event.start > now:
                return event
        return None

    @property
    def next_planned_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next planned outage time."""
        event = self._get_next_event_of_type(ConnectivityState.STATE_PLANNED_OUTAGE)
        return event.start if event else None

    @property
    def next_connectivity(self) -> datetime.date | datetime.datetime | None:
        """Get next connectivity time."""
        current_event = self.get_current_event()
        current_state = self._event_to_state(current_event)

        if current_state == ConnectivityState.STATE_PLANNED_OUTAGE:
            return current_event.end if current_event else None

        event = self._get_next_event_of_type(ConnectivityState.STATE_PLANNED_OUTAGE)
        return event.end if event else None

    @property
    def current_state(self) -> str:
        """Get the current state."""
        event = self.get_current_event()
        return self._event_to_state(event)

    @property
    def schedule_updated_on(self) -> datetime.datetime | None:
        """Get the schedule last updated timestamp."""
        return self.api.get_updated_on()

    @property
    def region_name(self) -> str:
        """Get the configured region name."""
        return self.translations.get(REGION_SELECTION_DTEK_KEY)

    @property
    def provider_name(self) -> str:
        """Get the configured provider name."""
        return ""

    def get_current_event(self) -> CalendarEvent | None:
        """Get the event at the present time."""
        return self.get_event_at(dt_utils.now())

    def get_event_at(self, at: datetime.datetime) -> CalendarEvent | None:
        """Get the event at a given time."""
        event = self.api.get_current_event(at)
        return self._get_calendar_event(event)

    def get_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Get all events."""
        events = self.api.get_events(start_date, end_date)
        return [self._get_calendar_event(event) for event in events]

    def _get_calendar_event(
        self, event: PlannedOutageEvent | None
    ) -> CalendarEvent | None:
        """Transform an event into a CalendarEvent."""
        if not event:
            return None

        summary: str = self.event_name_map.get(event.event_type)
        if DEBUG:
            summary += (
                f" {event.start.date().day}.{event.start.date().month}"
                f"@{event.start.time()}"
                f"-{event.end.date().day}.{event.end.date().month}"
                f"@{event.end.time()}"
            )

        # noinspection PyTypeChecker
        output = CalendarEvent(
            summary=summary,
            start=event.start,
            end=event.end,
            description=event.event_type.value,
            uid=event.event_type.value,
        )
        LOGGER.debug("Calendar Event: %s", output)
        return output

    def _event_to_state(self, event: CalendarEvent | None) -> ConnectivityState:
        if not event:
            return ConnectivityState.STATE_NORMAL

        if event.uid == PlannedOutageEventType.DEFINITE.value:
            return ConnectivityState.STATE_PLANNED_OUTAGE

        return ConnectivityState.STATE_NORMAL
