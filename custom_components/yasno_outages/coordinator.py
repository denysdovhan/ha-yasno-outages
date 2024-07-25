"""Coordinator for Yasno outages integration."""

import datetime
import logging

from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_utils

from .api import YasnoOutagesApi
from .const import (
    CONF_CITY,
    CONF_GROUP,
    DEFAULT_CITY,
    DOMAIN,
    EVENT_NAME_MAYBE,
    EVENT_NAME_OFF,
    STATE_MAYBE,
    STATE_OFF,
    STATE_ON,
    TRANSLATION_KEY_EVENT_MAYBE,
    TRANSLATION_KEY_EVENT_OFF,
    UPDATE_INTERVAL,
)

LOGGER = logging.getLogger(__name__)

TIMEFRAME_TO_CHECK = datetime.timedelta(hours=24)


class YasnoOutagesCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Yasno outages data."""

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
        self.city = config_entry.options.get(
            CONF_CITY,
            config_entry.data.get(CONF_CITY),
        )
        self.group = config_entry.options.get(
            CONF_GROUP,
            config_entry.data.get(CONF_GROUP),
        )

        if not self.city:
            LOGGER.warning("City not set in configuration. Setting to default.")
            self.city = DEFAULT_CITY

        self.api = YasnoOutagesApi(city=self.city, group=self.group)

    @property
    def event_name_map(self) -> dict:
        """Return a mapping of event names to translations."""
        return {
            EVENT_NAME_OFF: self.translations.get(TRANSLATION_KEY_EVENT_OFF),
            EVENT_NAME_MAYBE: self.translations.get(TRANSLATION_KEY_EVENT_MAYBE),
        }

    async def update_config(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        config_entry: ConfigEntry,
    ) -> None:
        """Update configuration."""
        new_city = config_entry.options.get(CONF_CITY)
        new_group = config_entry.options.get(CONF_GROUP)
        city_updated = new_city and new_city != self.city
        group_updated = new_group and new_group != self.group

        if city_updated or group_updated:
            LOGGER.debug("Updating group from %s -> %s", self.group, new_group)
            self.group = new_group
            self.api = YasnoOutagesApi(city=self.city, group=self.group)
            await self.async_refresh()
        else:
            LOGGER.debug("No group update necessary.")

    async def _async_update_data(self) -> None:
        """Fetch data from ICS file."""
        await self.async_fetch_translations()
        return await self.hass.async_add_executor_job(self.api.fetch_schedule)

    async def async_fetch_translations(self) -> None:
        """Fetch translations."""
        self.translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "common",
            [DOMAIN],
        )

    def _get_next_event_of_type(self, state_type: str) -> CalendarEvent | None:
        """Get the next event of a specific type."""
        now = dt_utils.now()
        # Sort events to handle multi-day spanning events correctly
        next_events = sorted(
            self.get_events_between(
                now,
                now + TIMEFRAME_TO_CHECK,
                translate=False,
            ),
            key=lambda event: event.start,
        )
        LOGGER.debug("Next events: %s", next_events)
        for event in next_events:
            if self._event_to_state(event) == state_type and event.start > now:
                return event
        return None

    @property
    def next_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next outage time."""
        event = self._get_next_event_of_type(STATE_OFF)
        LOGGER.debug("Next outage: %s", event)
        return event.start if event else None

    @property
    def next_possible_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next possible outage time."""
        event = self._get_next_event_of_type(STATE_MAYBE)
        LOGGER.debug("Next possible outage: %s", event)
        return event.start if event else None

    @property
    def next_connectivity(self) -> datetime.date | datetime.datetime | None:
        """Get next connectivity time."""
        now = dt_utils.now()
        current_event = self.get_event_at(now)
        # If current event is maybe, return the end time
        if self._event_to_state(current_event) == STATE_MAYBE:
            return current_event.end if current_event else None
        # Otherwise, return the next maybe event's end
        event = self._get_next_event_of_type(STATE_MAYBE)
        LOGGER.debug("Next connectivity: %s", event)
        return event.end if event else None

    @property
    def current_state(self) -> str:
        """Get the current state."""
        now = dt_utils.now()
        event = self.get_event_at(now)
        return self._event_to_state(event)

    def get_event_at(self, at: datetime.datetime) -> CalendarEvent | None:
        """Get the current event."""
        event = self.api.get_current_event(at)
        return self._get_calendar_event(event, translate=False)

    def get_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        *,
        translate: bool = True,
    ) -> list[CalendarEvent]:
        """Get all events."""
        events = self.api.get_events(start_date, end_date)
        return [
            self._get_calendar_event(event, translate=translate) for event in events
        ]  # type: ignore[return-type]

    def _get_calendar_event(
        self,
        event: dict | None,
        *,
        translate: bool = True,
    ) -> CalendarEvent | None:
        if not event:
            return None

        """Transform an event into a CalendarEvent."""
        event_summary = event.get("summary", None)
        event_start = event.get("start", None)
        event_end = event.get("end", None)
        translated_summary = self.event_name_map.get(event_summary, None)

        LOGGER.debug(
            "Transforming event: %s (%s -> %s)",
            event_summary,
            event_start,
            event_end,
        )

        return CalendarEvent(
            summary=translated_summary if translate else event_summary,
            start=event_start,
            end=event_end,
            description=event_summary,
        )

    def _event_to_state(self, event: CalendarEvent | None) -> str:
        summary = event.as_dict().get("summary") if event else None
        return {
            None: STATE_ON,
            EVENT_NAME_OFF: STATE_OFF,
            EVENT_NAME_MAYBE: STATE_MAYBE,
        }[summary]
