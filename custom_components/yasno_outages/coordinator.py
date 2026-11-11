"""Data coordinator for Yasno Outages integration."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_SCAN_INTERVAL, STATE_UNKNOWN
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_utils

from .api import OutageEvent, OutageEventType, YasnoApi, YasnoApiError
from .api.const import (
    API_STATUS_EMERGENCY_SHUTDOWNS,
    API_STATUS_NO_OUTAGES,
    API_STATUS_SCHEDULE_APPLIES,
    API_STATUS_WAITING_FOR_SCHEDULE,
    UA_TZ,
)
from .api.models import OutageSource
from .const import (
    CONF_ADDRESS_NAME,
    CONF_FILTER_PROBABLE,
    CONF_GROUP,
    CONF_PRESERVE_SCHEDULE,
    CONF_STATUS_ALL_DAY_EVENTS,
    DEFAULT_PRESERVE_SCHEDULE,
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
    STATE_STATUS_NO_OUTAGES,
    STATE_STATUS_SCHEDULE_APPLIES,
    STATE_STATUS_WAITING_FOR_SCHEDULE,
    STATUS_EMERGENCY_SHUTDOWNS_TEXT_FALLBACK,
    STATUS_NO_OUTAGES_TEXT_FALLBACK,
    STATUS_SCHEDULE_APPLIES_TEXT_FALLBACK,
    STATUS_WAITING_FOR_SCHEDULE_TEXT_FALLBACK,
    TRANSLATION_KEY_EVENT_PLANNED_OUTAGE,
    TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE,
    TRANSLATION_KEY_STATUS_EMERGENCY_SHUTDOWNS,
    TRANSLATION_KEY_STATUS_NO_OUTAGES,
    TRANSLATION_KEY_STATUS_SCHEDULE_APPLIES,
    TRANSLATION_KEY_STATUS_WAITING_FOR_SCHEDULE,
)
from .helpers import merge_consecutive_outages

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api.base import BaseYasnoApi

LOGGER = logging.getLogger(__name__)

EVENT_TYPE_STATE_MAP: dict[OutageEventType, str] = {
    OutageEventType.DEFINITE: STATE_OUTAGE,
    OutageEventType.NOT_PLANNED: STATE_NORMAL,
}

STATUS_STATE_MAP: dict[str, str] = {
    API_STATUS_NO_OUTAGES: STATE_STATUS_NO_OUTAGES,
    API_STATUS_SCHEDULE_APPLIES: STATE_STATUS_SCHEDULE_APPLIES,
    API_STATUS_WAITING_FOR_SCHEDULE: STATE_STATUS_WAITING_FOR_SCHEDULE,
    API_STATUS_EMERGENCY_SHUTDOWNS: STATE_STATUS_EMERGENCY_SHUTDOWNS,
}


def create_schedule_store(
    hass: HomeAssistant, entry_id: str
) -> Store[dict[str, list[list[float]]]]:
    """Create the store for one entry's last known schedule."""
    return Store(hass, 1, f"{DOMAIN}.schedule.{entry_id}", atomic_writes=True)


def is_outage_event(event: OutageEvent | None) -> bool:
    """Return True for outage events that should create calendar entries."""
    LOGGER.debug("Checking if event is an outage: %s", event)
    return bool(event and event.event_type != OutageEventType.NOT_PLANNED)


def find_next_outage(
    events: list[OutageEvent],
    now: datetime.datetime,
) -> OutageEvent | None:
    """Find the next outage event that starts after the given time."""
    for event in events:
        if event.start.timestamp() > now.timestamp():
            return event
    return None


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
        group: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=datetime.timedelta(
                minutes=config_entry.options.get(
                    CONF_SCAN_INTERVAL,
                    config_entry.data.get(CONF_SCAN_INTERVAL, 15),
                ),
            ),
        )
        self.hass = hass
        self.config_entry = config_entry
        self.translations = {}

        # Get configuration values
        self.region_id = api.planned.region_id
        self.provider_id = api.planned.provider_id
        self.group = group or config_entry.data.get(CONF_GROUP)
        self.address_name = config_entry.data.get(CONF_ADDRESS_NAME)
        self.filter_probable = config_entry.options.get(
            CONF_FILTER_PROBABLE,
            config_entry.data.get(CONF_FILTER_PROBABLE, True),
        )
        self.status_all_day_events = config_entry.options.get(
            CONF_STATUS_ALL_DAY_EVENTS,
            config_entry.data.get(CONF_STATUS_ALL_DAY_EVENTS, True),
        )
        self.preserve_schedule = config_entry.options.get(
            CONF_PRESERVE_SCHEDULE,
            config_entry.data.get(CONF_PRESERVE_SCHEDULE, DEFAULT_PRESERVE_SCHEDULE),
        )
        self._last_planned_events: dict[datetime.date, list[OutageEvent]] | None = None
        self._preserved_events: list[OutageEvent] = []

        if not self.region_id:
            region_required_msg = (
                "Region not set in configuration - this should not happen "
                "with proper config flow"
            )
            region_error = "Region configuration is required"
            LOGGER.error(region_required_msg)
            raise ValueError(region_error)

        if not self.provider_id:
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

        self._provider_name = ""  # Cache the provider name
        self._schedule_location = f"{self.region_id}/{self.provider_id}/{self.group}"
        self._schedule_store = create_schedule_store(hass, config_entry.entry_id)

        # Use the provided API instance
        self.api = api

    async def _async_update_data(self) -> None:
        """Fetch data from new Yasno API."""
        await self.async_fetch_translations()

        # Cache current data before fetching (for fallback on API failure)
        planned_cache = self.api.planned.planned_outages_data
        probable_cache = self.api.probable.probable_outages_data

        # Fetch planned outages data
        try:
            await self.api.planned.fetch_data()
        except YasnoApiError:
            LOGGER.warning(
                "Failed to fetch planned outages, using cached data", exc_info=True
            )
            self.api.planned.planned_outages_data = planned_cache
        else:
            if self.preserve_schedule:
                await self._async_update_preserved_schedule()

        # Fetch probable outages data
        try:
            await self.api.probable.fetch_data()
        except YasnoApiError:
            LOGGER.warning(
                "Failed to fetch probable outages, using cached data", exc_info=True
            )
            self.api.probable.probable_outages_data = probable_cache

    async def _async_load_planned_schedule(
        self,
    ) -> dict[datetime.date, list[OutageEvent]]:
        """Load outage events for the entry's current region, provider, and group."""
        events_by_date: dict[datetime.date, list[OutageEvent]] = {}
        try:
            stored = await self._schedule_store.async_load()
            if not isinstance(stored, dict):
                return events_by_date

            for start_timestamp, end_timestamp in stored.get(
                self._schedule_location, []
            ):
                event = OutageEvent(
                    event_type=OutageEventType.DEFINITE,
                    start=datetime.datetime.fromtimestamp(start_timestamp, UA_TZ),
                    end=datetime.datetime.fromtimestamp(end_timestamp, UA_TZ),
                    source=OutageSource.PLANNED,
                )
                events_by_date.setdefault(event.start.date(), []).append(event)
        except HomeAssistantError, OSError, OverflowError, TypeError, ValueError:
            LOGGER.warning("Could not load the preserved schedule", exc_info=True)
            return {}

        return events_by_date

    def _read_planned_schedule(
        self,
    ) -> tuple[dict[datetime.date, str | None], list[OutageEvent]]:
        """Read the reported days and their slots, including non-outage slots."""
        reported_days = (
            (self.today_date, self.status_today),
            (self.tomorrow_date, self.status_tomorrow),
        )
        statuses = {date: status for date, status in reported_days if date is not None}
        if not statuses:
            return {}, []

        start = datetime.datetime.combine(min(statuses), datetime.time.min, UA_TZ)
        end = datetime.datetime.combine(
            max(statuses) + datetime.timedelta(days=1), datetime.time.min, UA_TZ
        )
        return statuses, self.api.planned.get_events_between(start, end)

    async def _async_update_preserved_schedule(self) -> None:
        """Keep the latest usable schedule by date and track emergency fallbacks."""
        self._preserved_events = []
        try:
            statuses, live_slots = self._read_planned_schedule()
        except KeyError, OverflowError, TypeError, ValueError:
            LOGGER.debug("Failed to read planned schedule for the cache", exc_info=True)
            return

        if not statuses:
            return

        cached_outages = self._last_planned_events
        if cached_outages is None:
            cached_outages = await self._async_load_planned_schedule()

        latest_outages = {}
        for date, status in sorted(statuses.items()):
            if status == STATE_STATUS_NO_OUTAGES:
                continue

            day_slots = [slot for slot in live_slots if slot.start.date() == date]
            if day_slots:
                outages = [slot for slot in day_slots if is_outage_event(slot)]
            else:
                outages = cached_outages.get(date, [])

            if not outages:
                continue

            latest_outages[date] = outages
            if not day_slots and status == STATE_STATUS_EMERGENCY_SHUTDOWNS:
                self._preserved_events.extend(outages)

        self._last_planned_events = latest_outages
        if latest_outages != cached_outages:
            await self._async_save_planned_schedule(latest_outages)

    async def _async_save_planned_schedule(
        self,
        outages_by_date: dict[datetime.date, list[OutageEvent]],
    ) -> None:
        """Save the latest outage intervals for this entry's schedule."""
        intervals = [
            [event.start.timestamp(), event.end.timestamp()]
            for outages in outages_by_date.values()
            for event in outages
        ]
        await self._schedule_store.async_save({self._schedule_location: intervals})

    def _event_to_state(self, event: OutageEvent | None) -> str:
        """Map outage event to electricity state."""
        return (
            EVENT_TYPE_STATE_MAP.get(event.event_type, STATE_UNKNOWN)
            if event
            else STATE_UNKNOWN
        )

    async def async_fetch_translations(self) -> None:
        """Fetch translations."""
        self.translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "common",
            [DOMAIN],
        )

    @property
    def event_summary_map(self) -> dict[OutageSource, str]:
        """Return localized summaries by source with fallbacks."""
        return {
            OutageSource.PLANNED: self.translations.get(
                TRANSLATION_KEY_EVENT_PLANNED_OUTAGE, PLANNED_OUTAGE_TEXT_FALLBACK
            ),
            OutageSource.PROBABLE: self.translations.get(
                TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE, PROBABLE_OUTAGE_TEXT_FALLBACK
            ),
        }

    @property
    def status_event_summary_map(self) -> dict[str, str]:
        """Return localized summaries for planned status events."""
        return {
            STATE_STATUS_NO_OUTAGES: self.translations.get(
                TRANSLATION_KEY_STATUS_NO_OUTAGES,
                STATUS_NO_OUTAGES_TEXT_FALLBACK,
            ),
            STATE_STATUS_SCHEDULE_APPLIES: self.translations.get(
                TRANSLATION_KEY_STATUS_SCHEDULE_APPLIES,
                STATUS_SCHEDULE_APPLIES_TEXT_FALLBACK,
            ),
            STATE_STATUS_WAITING_FOR_SCHEDULE: self.translations.get(
                TRANSLATION_KEY_STATUS_WAITING_FOR_SCHEDULE,
                STATUS_WAITING_FOR_SCHEDULE_TEXT_FALLBACK,
            ),
            STATE_STATUS_EMERGENCY_SHUTDOWNS: self.translations.get(
                TRANSLATION_KEY_STATUS_EMERGENCY_SHUTDOWNS,
                STATUS_EMERGENCY_SHUTDOWNS_TEXT_FALLBACK,
            ),
        }

    @property
    def region_name(self) -> str:
        """Get the configured region name."""
        region = self.api.get_region_by_id(self.region_id)
        return region["value"] if region else ""

    @property
    def provider_name(self) -> str:
        """Get the configured provider name."""
        # Return cached name if available (but apply simplification first)
        if self._provider_name:
            return simplify_provider_name(self._provider_name)

        # Fallback to lookup if not cached yet
        if not self.api.regions_data:
            return ""

        provider = self.api.get_provider_by_id(self.region_id, self.provider_id)
        if provider:
            # Cache the simplified name
            self._provider_name = provider["name"]
            return simplify_provider_name(self._provider_name)

        return ""

    @property
    def current_event(self) -> OutageEvent | None:
        """Get the current planned event (including NotPlanned events)."""
        try:
            return self.api.planned.get_current_event(dt_utils.now())
        except Exception:  # noqa: BLE001, RUF100
            LOGGER.warning(
                "Failed to get current event, sensors will show unknown state",
                exc_info=True,
            )
            return None

    @property
    def current_state(self) -> str:
        """Get the current state."""
        if event := self.current_event:
            return self._event_to_state(event)

        # Yasno omits a current slot when the day status is "No Outages".
        if self.status_today == STATE_STATUS_NO_OUTAGES:
            return STATE_NORMAL

        return STATE_UNKNOWN

    @property
    def schedule_updated_on(self) -> datetime.datetime | None:
        """Get the schedule last updated timestamp."""
        return self.api.planned.get_updated_on()

    @property
    def today_date(self) -> datetime.date | None:
        """Get today's date."""
        return self.api.planned.get_today_date()

    @property
    def tomorrow_date(self) -> datetime.date | None:
        """Get tomorrow's date."""
        return self.api.planned.get_tomorrow_date()

    @property
    def status_today(self) -> str | None:
        """Get the status for today."""
        return STATUS_STATE_MAP.get(self.api.planned.get_status_today(), STATE_UNKNOWN)

    @property
    def status_tomorrow(self) -> str | None:
        """Get the status for tomorrow."""
        return STATUS_STATE_MAP.get(
            self.api.planned.get_status_tomorrow(), STATE_UNKNOWN
        )

    @property
    def next_planned_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next planned outage time."""
        now = dt_utils.now()
        events = self.get_merged_outages(
            self.api.planned,
            now,
            PLANNED_OUTAGE_LOOKAHEAD,
        )

        if event := find_next_outage(events, now):
            LOGGER.debug("Next planned outage: %s", event)
            return event.start

        return None

    @property
    def next_probable_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next probable outage time."""
        now = dt_utils.now()
        events = self.get_merged_outages(
            self.api.probable,
            now,
            PROBABLE_OUTAGE_LOOKAHEAD,
        )

        if event := find_next_outage(events, now):
            LOGGER.debug("Next probable outage: %s", event)
            return event.start

        return None

    @property
    def next_connectivity(self) -> datetime.date | datetime.datetime | None:
        """
        Get next connectivity time.

        Only planned events determine connectivity.
        Probable events are forecasts and do not affect connectivity calculation.
        """
        now = dt_utils.now()
        events = self.get_merged_outages(
            self.api.planned,
            now,
            PLANNED_OUTAGE_LOOKAHEAD,
        )

        # Check if we are in an outage
        for event in events:
            if event.start.timestamp() <= now.timestamp() < event.end.timestamp():
                return event.end

        # Find next outage
        if event := find_next_outage(events, now):
            LOGGER.debug("Next connectivity event: %s", event)
            return event.end

        return None

    def get_outage_at(
        self,
        api: BaseYasnoApi,
        at: datetime.datetime,
    ) -> OutageEvent | None:
        """Get an outage event at a given time from provided API."""
        try:
            event = api.get_current_event(at)
        except Exception:  # noqa: BLE001, RUF100
            LOGGER.warning("Failed to get current outage", exc_info=True)
            return None
        if not is_outage_event(event):
            return None
        return event

    def get_planned_outage_at(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the planned outage event at a given time."""
        return self.get_outage_at(self.api.planned, at)

    def get_probable_outage_at(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the probable outage event at a given time."""
        return self.get_outage_at(self.api.probable, at)

    def get_events_between(
        self,
        api: BaseYasnoApi,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get outage events within the date range for provided API."""
        try:
            events = api.get_events_between(start_date, end_date)
        except Exception:  # noqa: BLE001, RUF100
            LOGGER.warning(
                'Failed to get events between "%s" -> "%s"',
                start_date,
                end_date,
                exc_info=True,
            )
            return []

        filtered_events = [event for event in events if is_outage_event(event)]
        return sorted(filtered_events, key=lambda event: event.start)

    def get_planned_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get all planned events (filtering out NOT_PLANNED)."""
        return self.get_events_between(self.api.planned, start_date, end_date)

    def get_preserved_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get cached outage events that overlap the requested calendar range."""
        if not self._preserved_events:
            return []

        start = self.api.planned.to_ua_time(start_date).timestamp()
        end = self.api.planned.to_ua_time(end_date).timestamp()
        return [
            event
            for event in self._preserved_events
            if event.start.timestamp() <= end and event.end.timestamp() >= start
        ]

    def get_probable_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get all probable outage events within the date range."""
        return self.get_events_between(self.api.probable, start_date, end_date)

    def get_planned_dates(self) -> list[datetime.date]:
        """Get dates with planned outages."""
        return self.api.planned.get_planned_dates()

    def get_merged_outages(
        self,
        api: BaseYasnoApi,
        start_date: datetime.datetime,
        lookahead_days: int,
    ) -> list[OutageEvent]:
        """Get merged outage events for a lookahead period."""
        end_date = start_date + datetime.timedelta(days=lookahead_days)
        events = self.get_events_between(api, start_date, end_date)
        return merge_consecutive_outages(events)
