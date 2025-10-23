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
    CONF_GROUP,
    CONF_REGION,
    CONF_SERVICE,
    DOMAIN,
    EVENT_NAME_NORMAL,
    EVENT_NAME_OUTAGE,
    OUTAGE_STATE_NORMAL,
    OUTAGE_STATE_OUTAGE,
    OUTAGE_STATE_POSSIBLE,
    PROVIDER_DTEK_FULL,
    PROVIDER_DTEK_SHORT,
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

        # Get configuration values
        self.region = config_entry.options.get(
            CONF_REGION,
            config_entry.data.get(CONF_REGION),
        )
        self.service = config_entry.options.get(
            CONF_SERVICE,
            config_entry.data.get(CONF_SERVICE),
        )
        self.group = config_entry.options.get(
            CONF_GROUP,
            config_entry.data.get(CONF_GROUP),
        )

        if not self.region:
            region_required_msg = (
                "Region not set in configuration - this should not happen "
                "with proper config flow"
            )
            region_error = "Region configuration is required"
            LOGGER.error(region_required_msg)
            raise ValueError(region_error)

        if not self.service:
            service_required_msg = (
                "Service not set in configuration - this should not happen "
                "with proper config flow"
            )
            service_error = "Service configuration is required"
            LOGGER.error(service_required_msg)
            raise ValueError(service_error)

        if not self.group:
            group_required_msg = (
                "Group not set in configuration - this should not happen "
                "with proper config flow"
            )
            group_error = "Group configuration is required"
            LOGGER.error(group_required_msg)
            raise ValueError(group_error)

        # Initialize with names first, then we'll update with IDs when we fetch data
        self.region_id = None
        self.service_id = None
        self._provider_name = ""  # Cache the provider name

        # Initialize API and resolve IDs
        self.api = YasnoOutagesApi()
        # Note: We'll resolve IDs and update API during first data update

    @property
    def event_name_map(self) -> dict:
        """Return a mapping of event names to translations."""
        return {
            EVENT_NAME_OUTAGE: self.translations.get(TRANSLATION_KEY_EVENT_OFF),
            EVENT_NAME_NORMAL: self.translations.get(TRANSLATION_KEY_EVENT_MAYBE),
        }

    async def _resolve_ids(self) -> None:
        """Resolve region and service IDs from names."""
        if not self.api.regions_data:
            await self.api.fetch_regions()

        if self.region:
            region_data = self.api.get_region_by_name(self.region)
            if region_data:
                self.region_id = region_data["id"]
                if self.service:
                    service_data = self.api.get_service_by_name(
                        self.region, self.service
                    )
                    if service_data:
                        self.service_id = service_data["id"]
                        # Cache the provider name for device naming
                        self._provider_name = service_data["name"]

    async def _async_update_data(self) -> None:
        """Fetch data from new Yasno API."""
        await self.async_fetch_translations()

        # Resolve IDs if not already resolved
        if self.region_id is None or self.service_id is None:
            await self._resolve_ids()

            # Update API with resolved IDs
            self.api = YasnoOutagesApi(
                region_id=self.region_id,
                service_id=self.service_id,
                group=self.group,
            )

        # Fetch outages data (now async with aiohttp, not blocking)
        await self.api.fetch_data()

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
        event = self._get_next_event_of_type(OUTAGE_STATE_OUTAGE)
        LOGGER.debug("Next outage: %s", event)
        return event.start if event else None

    @property
    def next_possible_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next possible outage time."""
        current_event = self.get_current_event()

        # If currently in any outage state, return end time (when it ends)
        current_state = self._event_to_state(current_event)
        if current_state in [OUTAGE_STATE_OUTAGE, OUTAGE_STATE_POSSIBLE]:
            return current_event.end if current_event else None

        # Otherwise, return the start of the next outage
        event = self._get_next_event_of_type(OUTAGE_STATE_POSSIBLE)
        LOGGER.debug("Next possible outage: %s", event)
        return event.start if event else None

    @property
    def next_connectivity(self) -> datetime.date | datetime.datetime | None:
        """Get next connectivity time."""
        current_event = self.get_current_event()
        current_state = self._event_to_state(current_event)

        # If currently in any outage state, return when it ends
        if current_state in [OUTAGE_STATE_OUTAGE, OUTAGE_STATE_POSSIBLE]:
            return current_event.end if current_event else None

        # Otherwise, return the end of the next possible outage
        event = self._get_next_event_of_type(OUTAGE_STATE_POSSIBLE)
        LOGGER.debug("Next connectivity: %s", event)
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
        return self.region or ""

    @property
    def provider_name(self) -> str:
        """Get the configured provider (service provider) name."""
        # Return cached name if available (but apply simplification first)
        if self._provider_name:
            return self._simplify_provider_name(self._provider_name)

        # Fallback to lookup if not cached yet
        if not self.api.regions_data:
            return ""
        region_data = self.api.get_region_by_name(self.region)
        if not region_data:
            return ""
        services = region_data.get("dsos", [])
        for service in services:
            if service.get("name") == self.service:
                provider_name = service.get("name", "")
                # Cache the simplified name
                self._provider_name = provider_name
                return self._simplify_provider_name(provider_name)
        return ""

    def get_current_event(self) -> CalendarEvent | None:
        """Get the event at the present time."""
        return self.get_event_at(dt_utils.now())

    def get_event_at(self, at: datetime.datetime) -> CalendarEvent | None:
        """Get the event at a given time."""
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

        # Map event names to states
        if summary == EVENT_NAME_OUTAGE:
            return OUTAGE_STATE_OUTAGE
        if summary == EVENT_NAME_NORMAL:
            return OUTAGE_STATE_NORMAL
        if summary is None:
            return OUTAGE_STATE_NORMAL

        LOGGER.warning("Unknown event summary: %s", summary)
        return OUTAGE_STATE_NORMAL

    def _simplify_provider_name(self, provider_name: str) -> str:
        """Simplify provider names for cleaner display in device names."""
        # Replace long DTEK provider names with just "ДТЕК"
        if PROVIDER_DTEK_FULL in provider_name.upper():
            return PROVIDER_DTEK_SHORT

        # Add more provider simplifications here as needed
        return provider_name
