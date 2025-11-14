"""Data coordinator for Yasno Outages integration."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

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
    PROVIDER_DTEK_FULL,
    PROVIDER_DTEK_SHORT,
    STATE_NORMAL,
    STATE_OUTAGE,
    STATE_STATUS_EMERGENCY_SHUTDOWNS,
    STATE_STATUS_SCHEDULE_APPLIES,
    STATE_STATUS_WAITING_FOR_SCHEDULE,
    TRANSLATION_KEY_EVENT_OUTAGE,
    TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE,
    UPDATE_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

TIMEFRAME_TO_CHECK = datetime.timedelta(hours=24)


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
        # Note: We'll resolve IDs and update API during first data update

    @property
    def event_name_map(self) -> dict:
        """Return a mapping of event names to translations."""
        return {
            OutageEventType.DEFINITE.value: self.translations.get(
                TRANSLATION_KEY_EVENT_OUTAGE
            ),
        }

    @property
    def probable_event_name_map(self) -> dict:
        """Return a mapping of probable event names to translations."""
        return {
            OutageEventType.DEFINITE.value: self.translations.get(
                TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE
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
            self.get_planned_events_between(
                now,
                now + TIMEFRAME_TO_CHECK,
            ),
            key=lambda _: _.start,
        )
        LOGGER.debug("Next events: %s", next_events)
        for event in next_events:
            if self._event_to_state(event) == state_type and event.start > now:
                return event
        return None

    @property
    def next_planned_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next planned outage time."""
        event = self._get_next_event_of_type(STATE_OUTAGE)
        LOGGER.debug("Next planned outage: %s", event)
        return event.start if event else None

    @property
    def next_connectivity(self) -> datetime.date | datetime.datetime | None:
        """Get next connectivity time."""
        current_event = self.get_planned_current_event()
        current_state = self._event_to_state(current_event)

        # If currently in outage state, return when it ends
        if current_state == STATE_OUTAGE:
            return current_event.end if current_event else None

        # Otherwise, return the end of the next outage
        event = self._get_next_event_of_type(STATE_OUTAGE)
        LOGGER.debug("Next connectivity: %s", event)
        return event.end if event else None

    @property
    def current_state(self) -> str:
        """Get the current state."""
        event = self.get_planned_current_event()
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

    def get_planned_current_event(self) -> CalendarEvent | None:
        """Get the planned event at the present time."""
        return self.get_event_at(dt_utils.now())

    def get_event_at(self, at: datetime.datetime) -> CalendarEvent | None:
        """Get the event at a given time."""
        event = self.api.planned.get_current_event(at)
        # Filter out NOT_PLANNED events
        if event and event.event_type == OutageEventType.NOT_PLANNED:
            return None
        return self._get_calendar_event(event)

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
        calendar_events = [self._get_calendar_event(event) for event in filtered_events]
        return [e for e in calendar_events if e is not None]

    def _get_calendar_event(
        self,
        event: OutageEvent | None,
    ) -> CalendarEvent | None:
        """Transform an event into a CalendarEvent."""
        if not event:
            return None

        event_type = event.event_type.value
        summary = self.event_name_map.get(event_type)

        output = CalendarEvent(
            summary=summary,
            start=event.start,
            end=event.end,
            description=event_type,
            uid=event_type,
        )
        LOGGER.debug("Calendar Event: %s", output)
        return output

    def _event_to_state(self, event: CalendarEvent | None) -> str | None:
        if not event:
            return STATE_NORMAL

        # Map event types to states using uid field
        if event.uid == OutageEventType.DEFINITE.value:
            return STATE_OUTAGE

        LOGGER.warning("Unknown event type: %s", event.uid)
        return STATE_NORMAL

    def get_probable_current_event_at(
        self, at: datetime.datetime
    ) -> CalendarEvent | None:
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

                return CalendarEvent(
                    summary=self.probable_event_name_map.get(
                        OutageEventType.DEFINITE.value
                    ),
                    start=event_start,
                    end=event_end,
                    description=OutageEventType.DEFINITE.value,
                    uid=f"probable-{event_start.isoformat()}",
                )

        return None

    def get_probable_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Get all probable outage events within the date range."""
        events = self.api.probable.get_events_between(start_date, end_date)
        # Transform to CalendarEvents
        return [
            CalendarEvent(
                summary=self.probable_event_name_map.get(
                    OutageEventType.DEFINITE.value
                ),
                start=event.start,
                end=event.end,
                description=OutageEventType.DEFINITE.value,
                uid=f"probable-{event.start.isoformat()}",
            )
            for event in events
        ]

    @property
    def next_probable_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next probable outage time."""
        now = dt_utils.now()
        # Check events for the next week
        probable_events = self.get_probable_events_between(
            now,
            now + datetime.timedelta(days=7),
        )

        # Find first event that starts after now
        for event in probable_events:
            if event.start > now:
                return event.start

        return None
