"""Data coordinator for Yasno Outages integration."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Literal

from homeassistant.components.calendar import CalendarEvent
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_utils

from .api import OutageEvent, OutageEventType, YasnoApi
from .api.const import (
    API_STATUS_EMERGENCY_SHUTDOWNS,
    API_STATUS_SCHEDULE_APPLIES,
    API_STATUS_WAITING_FOR_SCHEDULE,
)
from .const import (
    CONF_GROUP,
    CONF_PROVIDER,
    CONF_REGION,
    DOMAIN,
    PLANNED_OUTAGE_LOOKAHEAD,
    PLANNED_OUTAGE_TEXT_FALLBACK,
    PROBABLE_OUTAGE_LOOKAHEAD,
    PROBABLE_OUTAGE_TEXT_FALLBACK,
    PROVIDER_DTEK_FULL,
    PROVIDER_DTEK_SHORT,
    STATE_NORMAL,
    STATE_OUTAGE,
    STATE_STATUS_EMERGENCY_SHUTDOWNS,
    STATE_STATUS_SCHEDULE_APPLIES,
    STATE_STATUS_WAITING_FOR_SCHEDULE,
    TRANSLATION_KEY_EVENT_PLANNED_OUTAGE,
    TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE,
    UPDATE_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)


def simplify_provider_name(provider_name: str) -> str:
    """Simplify provider names for cleaner display in device names."""
    # Replace long DTEK provider names with just "ДТЕК"
    if PROVIDER_DTEK_FULL in provider_name.upper():
        return PROVIDER_DTEK_SHORT

    # Add more provider simplifications here as needed
    return provider_name


class YasnoOutagesCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Yasno outages data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: YasnoApi,
    ) -> None:
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
        self.provider = config_entry.options.get(
            CONF_PROVIDER,
            config_entry.data.get(CONF_PROVIDER),
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

        if not self.provider:
            provider_required_msg = (
                "Provider not set in configuration - this should not happen "
                "with proper config flow"
            )
            provider_error = "Provider configuration is required"
            LOGGER.error(provider_required_msg)
            raise ValueError(provider_error)

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
        self.provider_id = None
        self._provider_name = ""  # Cache the provider name

        # Use the provided API instance
        self.api = api

    async def _async_update_data(self) -> None:
        """Fetch data from new Yasno API."""
        await self.async_fetch_translations()

        # Resolve IDs if not already resolved
        if self.region_id is None or self.provider_id is None:
            await self._resolve_ids()

            # Update API with resolved IDs
            self.api = YasnoApi(
                region_id=self.region_id,
                provider_id=self.provider_id,
                group=self.group,
            )

        # Fetch planned outages data
        try:
            await self.api.planned.fetch_data()
        except Exception:
            LOGGER.exception("Failed to fetch planned outages data")

        # Fetch probable outages data
        try:
            await self.api.probable.fetch_data()
        except Exception:  # noqa: BLE001
            LOGGER.warning("Failed to fetch probable outages data", exc_info=True)

    async def _resolve_ids(self) -> None:
        """Resolve region and provider IDs from names."""
        if not self.api.regions_data:
            await self.api.fetch_regions()

        if self.region:
            region_data = self.api.get_region_by_name(self.region)
            if region_data:
                self.region_id = region_data["id"]
                if self.provider:
                    provider_data = self.api.get_provider_by_name(
                        self.region,
                        self.provider,
                    )
                    if provider_data:
                        self.provider_id = provider_data["id"]
                        # Cache the provider name for device naming
                        self._provider_name = provider_data["name"]

    async def async_fetch_translations(self) -> None:
        """Fetch translations."""
        self.translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "common",
            [DOMAIN],
        )

    @property
    def event_summary_map(self) -> dict[str, dict[str, str]]:
        """Return localized summaries by source and event type with fallbacks."""
        return {
            "planned": self.translations.get(
                TRANSLATION_KEY_EVENT_PLANNED_OUTAGE, PLANNED_OUTAGE_TEXT_FALLBACK
            ),
            "probable": self.translations.get(
                TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE, PROBABLE_OUTAGE_TEXT_FALLBACK
            ),
        }

    @property
    def status_state_map(self) -> dict:
        """Return a mapping of status names to translations."""
        return {
            API_STATUS_SCHEDULE_APPLIES: STATE_STATUS_SCHEDULE_APPLIES,
            API_STATUS_WAITING_FOR_SCHEDULE: STATE_STATUS_WAITING_FOR_SCHEDULE,
            API_STATUS_EMERGENCY_SHUTDOWNS: STATE_STATUS_EMERGENCY_SHUTDOWNS,
        }

    @property
    def region_name(self) -> str:
        """Get the configured region name."""
        return self.region or ""

    @property
    def provider_name(self) -> str:
        """Get the configured provider name."""
        # Return cached name if available (but apply simplification first)
        if self._provider_name:
            return simplify_provider_name(self._provider_name)

        # Fallback to lookup if not cached yet
        if not self.api.regions_data:
            return ""

        region_data = self.api.get_region_by_name(self.region)
        if not region_data:
            return ""

        providers = region_data.get("dsos", [])
        for provider in providers:
            if (provider_name := provider.get("name", "")) == self.provider:
                # Cache the simplified name
                self._provider_name = provider_name
                return simplify_provider_name(provider_name)

        return ""

    @property
    def current_state(self) -> str:
        """
        Get the current state.

        Only planned events determine current state.
        Probable events are forecasts and do not affect state.
        """
        event = self.get_planned_event_at(dt_utils.now())
        return self._event_to_state(event)

    @property
    def schedule_updated_on(self) -> datetime.datetime | None:
        """Get the schedule last updated timestamp."""
        return self.api.planned.get_updated_on()

    @property
    def status_today(self) -> str | None:
        """Get the status for today."""
        return self.status_state_map.get(self.api.planned.get_status_today())

    @property
    def status_tomorrow(self) -> str | None:
        """Get the status for tomorrow."""
        return self.status_state_map.get(self.api.planned.get_status_tomorrow())

    @property
    def next_planned_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next planned outage time."""
        event = self._get_next_event_of_type(STATE_OUTAGE)
        LOGGER.debug("Next planned outage: %s", event)
        return event.start if event else None

    @property
    def next_probable_outage(self) -> datetime.date | datetime.datetime | None:
        """
        Get the next probable outage time.

        This is a forecast based on weekly recurring patterns.
        """
        now = dt_utils.now()
        probable_events = self.get_probable_events_between(
            now,
            now + datetime.timedelta(days=PROBABLE_OUTAGE_LOOKAHEAD),
        )

        # Find first event that starts after now
        for event in probable_events:
            if event.start > now:
                return event.start

        return None

    @property
    def next_connectivity(self) -> datetime.date | datetime.datetime | None:
        """
        Get next connectivity time.

        Only planned events determine connectivity.
        Probable events are forecasts and do not affect connectivity calculation.
        """
        current_event = self.get_planned_event_at(dt_utils.now())
        current_state = self._event_to_state(current_event)

        # If currently in outage state, return when it ends
        if current_state == STATE_OUTAGE:
            return current_event.end if current_event else None

        # Otherwise, return the end of the next outage
        event = self._get_next_event_of_type(STATE_OUTAGE)
        LOGGER.debug("Next connectivity: %s", event)
        return event.end if event else None

    def get_planned_event_at(self, at: datetime.datetime) -> CalendarEvent | None:
        """Get the planned event at a given time."""
        event = self.api.planned.get_current_event(at)
        # Filter out NOT_PLANNED events
        if not event or event.event_type == OutageEventType.NOT_PLANNED:
            return None
        return self._build_calendar_event("planned", event)

    def get_planned_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Get all planned events (filtering out NOT_PLANNED)."""
        events = self.api.planned.get_events_between(start_date, end_date)
        # Filter out NOT_PLANNED events
        filtered_events = [
            event for event in events if event.event_type != OutageEventType.NOT_PLANNED
        ]
        planned_events = [
            self._build_calendar_event("planned", event) for event in filtered_events
        ]
        return sorted(planned_events, key=lambda e: e.start)

    def get_probable_event_at(self, at: datetime.datetime) -> CalendarEvent | None:
        """Get the probable outage event at a given time."""
        weekday = at.weekday()  # 0=Monday, 6=Sunday
        slots = self.api.probable.get_probable_slots_for_weekday(weekday)

        # Find slot that contains the current time
        minutes_since_midnight = at.hour * 60 + at.minute

        for slot in slots:
            # Only consider DEFINITE slots
            if slot.event_type != OutageEventType.DEFINITE:
                continue

            if slot.start <= minutes_since_midnight < slot.end:
                # Found matching slot, create event for today
                date = at.replace(hour=0, minute=0, second=0, microsecond=0)
                event_start = self.api.probable.minutes_to_time(slot.start, date)
                event_end = self.api.probable.minutes_to_time(slot.end, date)

                probable_event = OutageEvent(
                    start=event_start,
                    end=event_end,
                    event_type=OutageEventType.DEFINITE,
                )
                return self._build_calendar_event("probable", probable_event)

        return None

    def get_probable_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Get all probable outage events within the date range."""
        events = self.api.probable.get_events_between(start_date, end_date)
        # Transform to CalendarEvents
        probable_events = [
            self._build_calendar_event("probable", event) for event in events
        ]
        return sorted(probable_events, key=lambda e: e.start)

    def _build_calendar_event(
        self,
        source: Literal["planned", "probable"],
        event: OutageEvent,
    ) -> CalendarEvent:
        """Transform an outage event into a CalendarEvent for a given source."""
        event_type = event.event_type.value
        summary = self.event_summary_map.get(source, "Outage")

        output = CalendarEvent(
            summary=summary,
            start=event.start,
            end=event.end,
            description=event_type,
            uid=f"{source}-{event.start.isoformat()}",
        )
        LOGGER.debug("Calendar Event: %s", output)
        return output

    def _event_to_state(self, event: CalendarEvent | None) -> str | None:
        if not event:
            return STATE_NORMAL

        # Map event types to states using description field
        if event.description == OutageEventType.DEFINITE.value:
            return STATE_OUTAGE

        LOGGER.warning("Unknown event type: %s", event.description)
        return STATE_NORMAL

    def _get_next_event_of_type(self, state_type: str) -> CalendarEvent | None:
        """Get the next event of a specific type."""
        now = dt_utils.now()
        # Sort events to handle multi-day spanning events correctly
        next_events = sorted(
            self.get_planned_events_between(
                now,
                now + datetime.timedelta(days=PLANNED_OUTAGE_LOOKAHEAD),
            ),
            key=lambda _: _.start,
        )
        LOGGER.debug("Next events: %s", next_events)
        for event in next_events:
            if self._event_to_state(event) == state_type and event.start > now:
                return event
        return None
