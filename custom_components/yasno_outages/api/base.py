"""Base API class for Yasno outages."""

import datetime
import logging

import aiohttp

from .const import REGIONS_ENDPOINT
from .models import OutageEvent, OutageEventType

LOGGER = logging.getLogger(__name__)


class BaseYasnoApi:
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

    def _parse_slots_to_events(
        self,
        slots: list[dict],
        date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Parse time slots into OutageEvent objects."""
        events = []

        for slot in slots:
            start_minutes = slot["start"]
            end_minutes = slot["end"]
            slot_type = slot["type"]

            try:
                event_type = OutageEventType(slot_type)
            except ValueError:
                LOGGER.warning("Unknown slot type: %s", slot_type)
                continue

            event_start = self.minutes_to_time(start_minutes, date)
            event_end = self.minutes_to_time(end_minutes, date)

            events.append(
                OutageEvent(
                    start=event_start,
                    end=event_end,
                    event_type=event_type,
                ),
            )

        return events
