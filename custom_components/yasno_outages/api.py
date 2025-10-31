"""API for Yasno outages."""

import datetime
import logging

import aiohttp

from .const import (
    EVENT_NAME_EMERGENCY,
    EVENT_NAME_NORMAL,
    EVENT_NAME_OUTAGE,
    PLANNED_OUTAGES_ENDPOINT,
    REGIONS_ENDPOINT,
    STATUS_EMERGENCY_SHUTDOWNS,
    STATUS_SCHEDULE_APPLIES,
)

LOGGER = logging.getLogger(__name__)


class YasnoOutagesApi:
    """Class to interact with Yasno outages API."""

    def __init__(
        self,
        region_id: int | None = None,
        service_id: int | None = None,
        group: str | None = None,
    ) -> None:
        """Initialize the YasnoOutagesApi."""
        self.region_id = region_id
        self.service_id = service_id
        self.group = group
        self.regions_data = None
        self.outages_data = None

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
        """Fetch regions and services data."""
        async with aiohttp.ClientSession() as session:
            self.regions_data = await self._get_route_data(session, REGIONS_ENDPOINT)

    async def fetch_outages_data(self) -> None:
        """Fetch outages data for the configured region and service."""
        if not self.region_id or not self.service_id:
            LOGGER.warning(
                "Region ID and Service ID must be set before fetching outages",
            )
            return

        url = PLANNED_OUTAGES_ENDPOINT.format(
            region_id=self.region_id,
            dso_id=self.service_id,
        )

        async with aiohttp.ClientSession() as session:
            self.outages_data = await self._get_route_data(session, url)

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

    def get_services_for_region(self, region_name: str) -> list[dict]:
        """Get services (dsos) for a specific region."""
        region = self.get_region_by_name(region_name)
        if not region:
            return []
        return region.get("dsos", [])

    def get_service_by_name(self, region_name: str, service_name: str) -> dict | None:
        """Get service (dso) data by region and service name."""
        services = self.get_services_for_region(region_name)
        for service in services:
            if service["name"] == service_name:
                return service
        return None

    def get_groups(self) -> list[str]:
        """Get groups from outages data."""
        if not self.outages_data:
            return []
        return list(self.outages_data.keys())

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
    ) -> list[dict]:
        """Parse schedule for a single day."""
        events = []
        slots = day_data.get("slots", [])

        for slot in slots:
            start_minutes = slot["start"]
            end_minutes = slot["end"]
            slot_type = slot["type"]

            # Map NotPlanned to NORMAL event
            if slot_type == "NotPlanned":
                slot_type = EVENT_NAME_NORMAL
            elif slot_type == "Definite":
                slot_type = EVENT_NAME_OUTAGE
            else:
                continue

            event_start = self._minutes_to_time(start_minutes, date)
            event_end = self._minutes_to_time(end_minutes, date)

            events.append(
                {
                    "summary": slot_type,
                    "start": event_start,
                    "end": event_end,
                },
            )

        return events

    def _get_group_data(self) -> dict | None:
        """Get data for the configured group."""
        if not self.outages_data or self.group not in self.outages_data:
            return None
        return self.outages_data[self.group]

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

    def get_current_event(self, at: datetime.datetime) -> dict | None:
        """Get the current event."""
        all_events = self.get_events(at, at + datetime.timedelta(days=1))
        for event in all_events:
            if event["start"] <= at < event["end"]:
                return event
        return None

    def get_events(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[dict]:
        """Get all events within the date range."""
        if not self.outages_data or self.group not in self.outages_data:
            return []

        events = []
        group_data = self._get_group_data()
        if not group_data:
            return events

        # Check today
        # Parse date with timezone from API
        today_api_date = None
        if "today" in group_data and "date" in group_data["today"]:
            try:
                today_api_date = datetime.datetime.fromisoformat(group_data["today"]["date"])
            except (ValueError, TypeError):
                LOGGER.warning("Failed to parse today's date from API")

        # If we have API date, use its timezone, otherwise use start_date
        today_date = (today_api_date or start_date).replace(hour=0, minute=0, second=0, microsecond=0)
        if "today" in group_data:
            today_status = group_data["today"].get("status")
            
            # Handle emergency shutdowns
            if today_status == STATUS_EMERGENCY_SHUTDOWNS:
                events.append({
                    "summary": EVENT_NAME_EMERGENCY,
                    "start": today_date,
                    "end": today_date.replace(hour=23, minute=59, second=59, microsecond=999999),
                })
            # Handle normal schedule
            elif today_status == STATUS_SCHEDULE_APPLIES:
                today_events = self._parse_day_schedule(group_data["today"], today_date)
                events.extend(today_events)

        # Check tomorrow if within range
        # Parse tomorrow's date with timezone from API
        tomorrow_api_date = None
        if "tomorrow" in group_data and "date" in group_data["tomorrow"]:
            try:
                tomorrow_api_date = datetime.datetime.fromisoformat(group_data["tomorrow"]["date"])
            except (ValueError, TypeError):
                LOGGER.warning("Failed to parse tomorrow's date from API")

        # If we have API date, use its timezone, otherwise add 1 day to today_date
        tomorrow_date = tomorrow_api_date or (today_date + datetime.timedelta(days=1))
        if tomorrow_date <= end_date and "tomorrow" in group_data:
            tomorrow_status = group_data["tomorrow"].get("status")
            
            # Handle emergency shutdowns
            if tomorrow_status == STATUS_EMERGENCY_SHUTDOWNS:
                events.append({
                    "summary": EVENT_NAME_EMERGENCY,
                    "start": tomorrow_date,
                    "end": tomorrow_date.replace(hour=23, minute=59, second=59, microsecond=999999),
                })
            # Handle normal schedule
            elif tomorrow_status == STATUS_SCHEDULE_APPLIES:
                tomorrow_events = self._parse_day_schedule(
                    group_data["tomorrow"],
                    tomorrow_date,
                )
                events.extend(tomorrow_events)

        # Sort events by start time and filter by date range
        events = sorted(events, key=lambda event: event["start"])

        # Filter events that intersect with the requested range
        return [
            event
            for event in events
            if (
                start_date <= event["start"] <= end_date
                or start_date <= event["end"] <= end_date
                or event["start"] <= start_date <= event["end"]
                or event["start"] <= end_date <= event["end"]
            )
        ]

    async def fetch_data(self) -> None:
        """Fetch all required data."""
        # Regions are fetched by _resolve_ids, so only fetch outages
        await self.fetch_outages_data()
