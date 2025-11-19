"""Base API class for Yasno outages."""

import datetime
import logging
from abc import ABC, abstractmethod

import aiohttp

from .const import REGIONS_ENDPOINT
from .models import OutageEvent, OutageEventType, OutageSlot, OutageSource

LOGGER = logging.getLogger(__name__)


class BaseYasnoApi(ABC):
    """Base class for Yasno API interactions."""

    def __init__(
        self,
        region_id: int | None = None,
        provider_id: int | None = None,
        group: str | None = None,
    ) -> None:
        """Initialize the BaseYasnoApi."""
        self.region_id = region_id
        self.provider_id = provider_id
        self.group = group
        self.regions_data = None

    async def _get_data(
        self,
        session: aiohttp.ClientSession,
        url: str,
        timeout_secs: int = 60,
    ) -> dict | None:
        """Fetch data from the given URL."""
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout_secs),
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError:
            LOGGER.exception("Error fetching data from %s", url)
            return None

    async def fetch_regions(self) -> None:
        """Fetch regions and providers data."""
        async with aiohttp.ClientSession() as session:
            self.regions_data = await self._get_data(session, REGIONS_ENDPOINT)

    def get_regions(self) -> list[dict]:
        """Get a list of available regions."""
        if not self.regions_data:
            return []
        return self.regions_data

    def get_region_by_name(self, region_name: str) -> dict | None:
        """Get region data by name."""
        for region in self.get_regions():
            if region["value"] == region_name:
                return region
        return None

    def get_providers_for_region(self, region_name: str) -> list[dict]:
        """Get providers (dsos) for a specific region."""
        region = self.get_region_by_name(region_name)
        if not region:
            return []
        return region.get("dsos", [])

    def get_provider_by_name(self, region_name: str, provider_name: str) -> dict | None:
        """Get provider (dso) data by region and provider name."""
        providers = self.get_providers_for_region(region_name)
        for provider in providers:
            if provider["name"] == provider_name:
                return provider
        return None

    def get_next_event(
        self,
        at: datetime.datetime,
        event_type: OutageEventType = OutageEventType.DEFINITE,
        lookahead_days: int = 1,
    ) -> OutageEvent | None:
        """Return outage event that starts after provided time."""
        horizon = at + datetime.timedelta(days=lookahead_days)
        events = sorted(
            self.get_events_between(at, horizon),
            key=lambda event: event.start,
        )

        for event in events:
            if event.event_type != event_type:
                continue
            if event.start > at:
                return event

        return None

    @staticmethod
    def minutes_to_time(
        minutes: int,
        date: datetime.datetime,
    ) -> datetime.datetime:
        """Convert minutes from start of day to datetime."""
        hours = minutes // 60
        mins = minutes % 60
        # Handle end of day (24:00) - use midnight of next day
        if hours == 24:  # noqa: PLR2004
            tomorrow = date + datetime.timedelta(days=1)
            return tomorrow.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        return date.replace(hour=hours, minute=mins, second=0, microsecond=0)

    @staticmethod
    def _parse_raw_slots(slots: list[dict]) -> list[OutageSlot]:
        """Parse raw slot dictionaries into OutageSlot objects."""
        parsed_slots = []
        for slot in slots:
            try:
                event_type = OutageEventType(slot["type"])
                parsed_slots.append(
                    OutageSlot(
                        start=slot["start"],
                        end=slot["end"],
                        event_type=event_type,
                    ),
                )
            except (ValueError, KeyError) as err:
                LOGGER.warning("Failed to parse slot %s: %s", slot, err)
                continue
        return parsed_slots

    @staticmethod
    def _parse_slots_to_events(
        slots: list[OutageSlot],
        date: datetime.datetime,
        source: OutageSource,
    ) -> list[OutageEvent]:
        """Convert OutageSlot instances to OutageEvent instances for a given date."""
        events = []

        for slot in slots:
            event_start = BaseYasnoApi.minutes_to_time(slot.start, date)
            event_end = BaseYasnoApi.minutes_to_time(slot.end, date)

            events.append(
                OutageEvent(
                    start=event_start,
                    end=event_end,
                    event_type=slot.event_type,
                    source=source,
                ),
            )

        return events

    @abstractmethod
    def get_current_event(self, at: datetime.datetime) -> OutageEvent | None:
        """Return outage event that is active at provided time."""

    @abstractmethod
    def get_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Return outage events that intersect provided range."""
