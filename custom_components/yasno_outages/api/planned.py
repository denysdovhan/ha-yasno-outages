"""Planned outages API for Yasno."""

import datetime
import logging
from typing import Literal

import aiohttp

from .base import BaseYasnoApi
from .const import (
    API_KEY_DATE,
    API_KEY_STATUS,
    API_KEY_TODAY,
    API_KEY_TOMORROW,
    PLANNED_OUTAGES_ENDPOINT,
)
from .models import OutageEvent

LOGGER = logging.getLogger(__name__)


class PlannedOutagesApi(BaseYasnoApi):
    """API for fetching planned outages data."""

    def __init__(
        self,
        region_id: int | None = None,
        provider_id: int | None = None,
        group: str | None = None,
    ) -> None:
        """Initialize the PlannedOutagesApi."""
        super().__init__(region_id, provider_id, group)
        self.planned_outages_data = None

    async def fetch_planned_outages_data(self) -> None:
        """Fetch planned outages data for the configured region and provider."""
        if not self.region_id or not self.provider_id:
            LOGGER.warning(
                "Region ID and Provider ID must be set before fetching planned outages",
            )
            return

        url = PLANNED_OUTAGES_ENDPOINT.format(
            region_id=self.region_id,
            dso_id=self.provider_id,
        )

        async with aiohttp.ClientSession() as session:
            self.planned_outages_data = await self._get_data(session, url)

    def get_groups(self) -> list[str]:
        """Get groups from planned outages data."""
        if not self.planned_outages_data:
            return []
        return list(self.planned_outages_data.keys())

    def get_planned_outages_data(self) -> dict | None:
        """Get data for the configured group."""
        if not self.planned_outages_data or self.group not in self.planned_outages_data:
            return None
        return self.planned_outages_data[self.group]

    def _parse_day_schedule(
        self,
        day_data: dict,
        date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Parse schedule for a single day."""
        slots = self._parse_raw_slots(day_data.get("slots", []))
        return self._parse_slots_to_events(slots, date)

    def _parse_day_events(
        self,
        group_data: dict,
        day_key: str,
    ) -> list[OutageEvent]:
        """Parse events for a specific day (today or tomorrow) from group data."""
        if day_key not in group_data:
            return []

        day_data = group_data[day_key]
        if API_KEY_DATE not in day_data:
            return []

        try:
            day_date = datetime.datetime.fromisoformat(day_data["date"])
            return self._parse_day_schedule(day_data, day_date)
        except (ValueError, TypeError) as err:
            LOGGER.warning("Failed to parse %s date: %s", day_key, err)
            return []

    def get_updated_on(self) -> datetime.datetime | None:
        """Get the updated on timestamp for the configured group."""
        group_data = self.get_planned_outages_data()
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

    def get_status_by_day(self, day: Literal["today", "tomorrow"]) -> str | None:
        """Get the status for a specific day."""
        group_data = self.get_planned_outages_data()
        if not group_data or day not in group_data:
            return None

        return group_data[day].get(API_KEY_STATUS)

    def get_status_today(self) -> str | None:
        """Get the status for today."""
        return self.get_status_by_day(API_KEY_TODAY)

    def get_status_tomorrow(self) -> str | None:
        """Get the status for tomorrow."""
        return self.get_status_by_day(API_KEY_TOMORROW)

    def get_current_event(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the current event."""
        all_events = self.get_events_between(at, at + datetime.timedelta(days=1))
        for event in all_events:
            if event.start <= at < event.end:
                return event
        return None

    def get_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get all events within the date range."""
        if not self.planned_outages_data or self.group not in self.planned_outages_data:
            return []

        events = []
        group_data = self.get_planned_outages_data()
        if not group_data:
            return events

        # Parse today and tomorrow events using the helper function
        events.extend(self._parse_day_events(group_data, API_KEY_TODAY))
        events.extend(self._parse_day_events(group_data, API_KEY_TOMORROW))

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
        # Regions are fetched by _resolve_ids, so only fetch planned outages
        await self.fetch_planned_outages_data()
