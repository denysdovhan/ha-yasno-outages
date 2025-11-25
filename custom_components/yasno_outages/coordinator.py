"""Data coordinator for Yasno Outages integration."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_utils

from .api import OutageEvent, OutageEventType, YasnoApi
from .api.const import (
    API_STATUS_EMERGENCY_SHUTDOWNS,
    API_STATUS_SCHEDULE_APPLIES,
    API_STATUS_WAITING_FOR_SCHEDULE,
)
from .api.models import OutageSource
from .const import (
    CONF_FILTER_PROBABLE,
    CONF_GROUP,
    CONF_PROVIDER,
    CONF_REGION,
    CONF_STATUS_ALL_DAY_EVENTS,
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
    STATUS_EMERGENCY_SHUTDOWNS_TEXT_FALLBACK,
    STATUS_SCHEDULE_APPLIES_TEXT_FALLBACK,
    STATUS_WAITING_FOR_SCHEDULE_TEXT_FALLBACK,
    TRANSLATION_KEY_EVENT_PLANNED_OUTAGE,
    TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE,
    TRANSLATION_KEY_STATUS_EMERGENCY_SHUTDOWNS,
    TRANSLATION_KEY_STATUS_SCHEDULE_APPLIES,
    TRANSLATION_KEY_STATUS_WAITING_FOR_SCHEDULE,
    UPDATE_INTERVAL,
)

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
    API_STATUS_SCHEDULE_APPLIES: STATE_STATUS_SCHEDULE_APPLIES,
    API_STATUS_WAITING_FOR_SCHEDULE: STATE_STATUS_WAITING_FOR_SCHEDULE,
    API_STATUS_EMERGENCY_SHUTDOWNS: STATE_STATUS_EMERGENCY_SHUTDOWNS,
}


def is_outage_event(event: OutageEvent | None) -> bool:
    """Return True for outage events that should create calendar entries."""
    LOGGER.debug("Checking if event is an outage: %s", event)
    return bool(event and event.event_type != OutageEventType.NOT_PLANNED)


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
        self.filter_probable = config_entry.options.get(
            CONF_FILTER_PROBABLE,
            config_entry.data.get(CONF_FILTER_PROBABLE, True),
        )
        self.status_all_day_events = config_entry.options.get(
            CONF_STATUS_ALL_DAY_EVENTS,
            config_entry.data.get(CONF_STATUS_ALL_DAY_EVENTS, True),
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
            try:
                await self._resolve_ids()
            except Exception as err:
                msg = f"Failed to resolve IDs: {err}"
                raise UpdateFailed(msg) from err

            # Update API with resolved IDs
            self.api = YasnoApi(
                region_id=self.region_id,
                provider_id=self.provider_id,
                group=self.group,
            )

        # Fetch planned outages data
        try:
            await self.api.planned.fetch_data()
        except Exception as err:
            msg = f"Failed to fetch planned outages data: {err}"
            raise UpdateFailed(msg) from err

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
    def current_event(self) -> OutageEvent | None:
        """Get the current outage event."""
        return self.api.planned.get_current_event(dt_utils.now())

    @property
    def current_state(self) -> str:
        """Get the current state."""
        return self._event_to_state(self.current_event)

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
        next_event = self.api.planned.get_next_event(
            dt_utils.now(),
            lookahead_days=PLANNED_OUTAGE_LOOKAHEAD,
        )
        if not is_outage_event(next_event):
            return None
        LOGGER.debug("Next planned outage: %s", next_event)
        return next_event.start

    @property
    def next_probable_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next probable outage time."""
        next_event = self.api.probable.get_next_event(
            dt_utils.now(),
            lookahead_days=PROBABLE_OUTAGE_LOOKAHEAD,
        )
        if not is_outage_event(next_event):
            return None
        LOGGER.debug("Next probable outage: %s", next_event)
        return next_event.start

    @property
    def next_connectivity(self) -> datetime.date | datetime.datetime | None:
        """
        Get next connectivity time.

        Only planned events determine connectivity.
        Probable events are forecasts and do not affect connectivity calculation.
        """
        current_event = self.get_planned_outage_at(dt_utils.now())
        current_state = self._event_to_state(current_event)

        if current_state == STATE_OUTAGE and current_event:
            return current_event.end

        next_event = self.api.planned.get_next_event(
            dt_utils.now(),
            lookahead_days=PLANNED_OUTAGE_LOOKAHEAD,
        )
        if not is_outage_event(next_event):
            return None
        LOGGER.debug("Next connectivity event: %s", next_event)
        return next_event.end

    def get_outage_at(
        self,
        api: BaseYasnoApi,
        at: datetime.datetime,
    ) -> OutageEvent | None:
        """Get an outage event at a given time from provided API."""
        try:
            event = api.get_current_event(at)
        except Exception:  # noqa: BLE001
            LOGGER.warning("Failed to get current outage", exc_info=True)
            return None
        if not is_outage_event(event):
            return None
        return event

    def get_planned_outage_at(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the planned event at a given time."""
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
        except Exception:  # noqa: BLE001
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
