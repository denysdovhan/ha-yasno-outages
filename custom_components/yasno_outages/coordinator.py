"""Coordinator for Yasno outages integration."""

import datetime
import logging

from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import YasnoOutagesApi
from .const import (
    CONF_GROUP,
    DOMAIN,
    EVENT_MAYBE,
    EVENT_OFF,
    TRANSLATION_KEY_EVENT_MAYBE,
    TRANSLATION_KEY_EVENT_OFF,
)

LOGGER = logging.getLogger(__name__)


class YasnoOutagesCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Yasno outages data."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=None,  # No polling, update manually
        )
        self.hass = hass
        self.translations = {}
        self.group = config_entry.options.get(
            CONF_GROUP,
            config_entry.data.get(CONF_GROUP),
        )
        self.api = YasnoOutagesApi(self.group)

    @property
    def event_name_map(self) -> dict:
        """Return a mapping of event names to translations."""
        return {
            EVENT_OFF: self.translations.get(TRANSLATION_KEY_EVENT_OFF),
            EVENT_MAYBE: self.translations.get(TRANSLATION_KEY_EVENT_MAYBE),
        }

    async def update_config(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        config_entry: ConfigEntry,
    ) -> None:
        """Update configuration."""
        new_group = config_entry.options.get(CONF_GROUP)
        if new_group and new_group != self.group:
            LOGGER.debug("Updating group from %s -> %s", self.group, new_group)
            self.group = new_group
            self.api = YasnoOutagesApi(self.group)
            await self.async_refresh()
        else:
            LOGGER.debug("No group update necessary.")

    async def _async_update_data(self) -> None:
        """Fetch data from ICS file."""
        try:
            await self.async_fetch_translations()
            return await self.hass.async_add_executor_job(self.api.fetch_calendar)
        except FileNotFoundError as err:
            LOGGER.exception("Cannot read file for group %s", self.group)
            msg = f"File not found: {err}"
            raise UpdateFailed(msg) from err

    async def async_fetch_translations(self) -> None:
        """Fetch translations."""
        LOGGER.debug("Fetching translations for %s", DOMAIN)
        self.translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "common",
            [DOMAIN],
        )
        LOGGER.debug("Translations loaded: %s", self.translations)

    def get_current_event(self, at: datetime.datetime) -> CalendarEvent:
        """Get the current event."""
        event = self.api.get_current_event(at)
        return self._to_calendar_event(event, translate=False)

    def get_events(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Get all events."""
        events = self.api.get_events(start_date, end_date)
        return [self._to_calendar_event(event) for event in events]

    def _to_calendar_event(
        self,
        event: dict | None,
        *,
        translate: bool = True,
    ) -> CalendarEvent:
        """Transform an event into a CalendarEvent."""
        if not event:
            return None

        event_summary = event.get("SUMMARY")
        translated_summary = self.event_name_map.get(event_summary)
        event_start = event.decoded("DTSTART")
        event_end = event.decoded("DTEND")

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
