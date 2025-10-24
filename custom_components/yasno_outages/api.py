"""API for Yasno outages."""

import datetime
import logging
from dataclasses import dataclass
from enum import Enum

import aiohttp

from .const import (
    BLOCK_KEY_STATUS,
    BLOCK_NAME_TODAY,
    BLOCK_NAME_TOMORROW,
    EVENT_NAME_NORMAL,
    EVENT_NAME_OUTAGE,
    PLANNED_OUTAGES_ENDPOINT,
    REGIONS_ENDPOINT,
    STATUS_SCHEDULE_APPLIES,
)

LOGGER = logging.getLogger(__name__)


class OutageEventType(str, Enum):
    """Outage event types."""

    DEFINITE = "Definite"
    NOT_PLANNED = "NotPlanned"


@dataclass
class OutageEvent:
    """Represents an outage event."""

    event_type: OutageEventType
    start: datetime.datetime
    end: datetime.datetime


class YasnoOutagesApi:
    """Class to interact with Yasno outages API."""

    def __init__(
        self,
        region_id: int | None = None,
        provider_id: int | None = None,
        group: str | None = None,
    ) -> None:
        """Initialize the YasnoOutagesApi."""
        self.region_id = region_id
        self.provider_id = provider_id
        self.group = group
        self.regions_data = None
        self.planned_outages_data = None

    async def _get_route_data(
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
            self.regions_data = await self._get_route_data(session, REGIONS_ENDPOINT)

    async def fetch_planned_outages_data(self) -> None:
        """Fetch outages data for the configured region and provider."""
        if not self.region_id or not self.provider_id:
            LOGGER.warning(
                "Region ID and Provider ID must be set before fetching outages",
            )
            return

        url = PLANNED_OUTAGES_ENDPOINT.format(
            region_id=self.region_id,
            dso_id=self.provider_id,
        )

        async with aiohttp.ClientSession() as session:
            self.planned_outages_data = await self._get_route_data(session, url)

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
        """Get providers for a specific region."""
        region = self.get_region_by_name(region_name)
        if not region:
            return []
        return region.get("dsos", [])

    def get_provider_by_name(self, region_name: str, provider_name: str) -> dict | None:
        """Get provider data by region and provider name."""
        providers = self.get_providers_for_region(region_name)
        for provider in providers:
            if provider["name"] == provider_name:
                return provider
        return None

    def get_groups(self) -> list[str]:
        """Get groups from outages data."""
        if not self.planned_outages_data:
            return []
        return list(self.planned_outages_data.keys())

    def _minutes_to_time(
        self,
        minutes: int,
        date: datetime.datetime,
    ) -> datetime.datetime:
        """Convert minutes from start of day to datetime."""
        hours = minutes // 60
        mins = minutes % 60

        # Handle end of day (24:00) - keep it as 23:59:59 to stay on same day
        if hours == 24:  # noqa: PLR2004
            return date.replace(hour=23, minute=59, second=59, microsecond=999999)

        return date.replace(hour=hours, minute=mins, second=0, microsecond=0)

    def _parse_day_schedule(
        self,
        day_data: dict,
        date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Parse schedule for a single day."""
        events = []
        slots = day_data.get("slots", [])

        for slot in slots:
            start_minutes = slot["start"]
            end_minutes = slot["end"]
            slot_type = slot["type"]

            if slot_type not in [EVENT_NAME_NORMAL, EVENT_NAME_OUTAGE]:
                continue

            event_start = self._minutes_to_time(start_minutes, date)
            event_end = self._minutes_to_time(end_minutes, date)

            events.append(
                OutageEvent(
                    start=event_start,
                    end=event_end,
                    event_type=OutageEventType(slot_type),
                ),
            )

        return events

    def _get_group_data(self) -> dict | None:
        """Get data for the configured group."""
        if not self.planned_outages_data or self.group not in self.planned_outages_data:
            return None
        return self.planned_outages_data[self.group]

    def get_updated_on(self) -> datetime.datetime | None:
        """Get the updated on timestamp for the configured group."""
        group_data = self._get_group_data()
        if not group_data or "updatedOn" not in group_data:
            return None

        try:
            return datetime.datetime.fromisoformat(group_data["updatedOn"])
        except (ValueError, TypeError):
            LOGGER.warning(
                "Failed to parse updatedOn timestamp: %s",
                group_data["updatedOn"],
            )
            return None

    def get_current_event(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the current event."""
        all_events = self.get_events(at, at + datetime.timedelta(days=1))
        for event in all_events:
            if event.start <= at < event.end:
                return event
        return None

    def get_events(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get all events within the date range."""
        if not self.planned_outages_data or self.group not in self.planned_outages_data:
            return []

        events = []
        group_data = self._get_group_data()
        if not group_data:
            return events

        # Check today
        today_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        if (
            group_data.get(BLOCK_NAME_TODAY, {}).get(BLOCK_KEY_STATUS)
            == STATUS_SCHEDULE_APPLIES
        ):
            today_events = self._parse_day_schedule(
                group_data[BLOCK_NAME_TODAY],
                today_date,
            )
            events.extend(today_events)

        # Check tomorrow if within range
        tomorrow_date = today_date + datetime.timedelta(days=1)
        if (
            tomorrow_date <= end_date
            and BLOCK_NAME_TOMORROW in group_data
            and group_data[BLOCK_NAME_TOMORROW].get(BLOCK_KEY_STATUS)
            == STATUS_SCHEDULE_APPLIES
        ):
            tomorrow_events = self._parse_day_schedule(
                group_data[BLOCK_NAME_TOMORROW],
                tomorrow_date,
            )
            events.extend(tomorrow_events)

        # Sort events by start time and filter by date range
        events = sorted(events, key=lambda event: event.start)

        # Filter events that intersect with the requested range
        return [
            event
            for event in events
            if (
                start_date <= event.start <= end_date
                or start_date <= event.end <= end_date
                or event.start <= start_date <= event.end
                or event.start <= end_date <= event.end
            )
        ]

    async def fetch_data(self) -> None:
        """Fetch all required data."""
        # Regions are fetched by _resolve_ids, so only fetch outages
        await self.fetch_planned_outages_data()
