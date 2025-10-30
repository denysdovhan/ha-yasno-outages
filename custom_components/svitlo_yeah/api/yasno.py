"""Yasno API client for Svitlo Yeah integration."""

from __future__ import annotations

import datetime
import logging

import aiohttp
from homeassistant.util import dt as dt_utils

from ..const import (
    BLOCK_KEY_STATUS,
    PLANNED_OUTAGES_ENDPOINT,
    REGIONS_ENDPOINT,
)
from ..models import (
    PlannedOutageEvent,
    PlannedOutageEventType,
    YasnoPlannedOutageDayStatus,
)

LOGGER = logging.getLogger(__name__)


def _minutes_to_time(minutes: int, dt: datetime.datetime) -> datetime.datetime:
    """Convert minutes from start of day to datetime."""
    hours = minutes // 60
    mins = minutes % 60

    # Handle end of day (24:00) - keep it as 23:59:59 to stay on same day
    if hours == 24:  # noqa: PLR2004
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    return dt.replace(hour=hours, minute=mins, second=0, microsecond=0)


def _parse_day_schedule(
    day_data: dict, dt: datetime.datetime
) -> list[PlannedOutageEvent]:
    """
    Parse schedule for a single day.

    {
      "3.1": {
        "today": {
          "slots": [
            {
              "start": 0,
              "end": 960,
              "type": "NotPlanned"
            },
            {
              "start": 960,
              "end": 1200,
              "type": "Definite"
            },
            {
              "start": 1200,
              "end": 1440,
              "type": "NotPlanned"
            }
          ],
          "date": "2025-10-27T00:00:00+02:00",
          "status": "ScheduleApplies"
        },
        "tomorrow": {
          "slots": [
            {
              "start": 0,
              "end": 900,
              "type": "NotPlanned"
            },
            {
              "start": 900,
              "end": 1080,
              "type": "Definite"
            },
            {
              "start": 1080,
              "end": 1440,
              "type": "NotPlanned"
            }
          ],
          "date": "2025-10-28T00:00:00+02:00",
          "status": "WaitingForSchedule"
        },
        "updatedOn": "2025-10-27T13:42:41+00:00"
      },
    }
    """
    events = []
    slots = day_data.get("slots", [])

    for slot in slots:
        start_minutes = slot["start"]
        end_minutes = slot["end"]
        slot_type = slot["type"]

        # parse only outages
        if slot_type not in [PlannedOutageEventType.DEFINITE.value]:
            continue

        event_start = _minutes_to_time(start_minutes, dt)
        event_end = _minutes_to_time(end_minutes, dt)

        events.append(
            PlannedOutageEvent(
                start=event_start,
                end=event_end,
                event_type=PlannedOutageEventType(slot_type),
            ),
        )

    return events


class YasnoApi:
    """Class to interact with Yasno API."""

    _cached_regions_data: list[dict] | None = None

    def __init__(
        self,
        region_id: int | None = None,
        provider_id: int | None = None,
        group: str | None = None,
    ) -> None:
        """Initialize the Yasno API."""
        self.region_id = region_id
        self.provider_id = provider_id
        self.group = group
        self.regions_data = None
        self.planned_outage_data = None

    async def _get_route_data(
        self,
        session: aiohttp.ClientSession,
        url: str,
        timeout_secs: int = 60,
    ) -> dict | list[dict] | None:
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

    async def fetch_yasno_regions(self) -> None:
        """Fetch regions and providers data."""
        if YasnoApi._cached_regions_data:
            self.regions_data = YasnoApi._cached_regions_data
            return

        async with aiohttp.ClientSession() as session:
            self.regions_data = (
                YasnoApi._cached_regions_data
            ) = await self._get_route_data(session, REGIONS_ENDPOINT)

    async def fetch_planned_outage_data(self) -> None:
        """Fetch outage data for the configured region and provider."""
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
            self.planned_outage_data = await self._get_route_data(session, url)

        # DEBUG. DO NOT COMMIT UNCOMMENTED!
        """
        self.planned_outage_data = {
            "3.1": {
                "today": {
                    "slots": [],
                    "date": "2025-10-27T00:00:00+02:00",
                    "status": "EmergencyShutdowns"
                },
                "tomorrow": {
                    "slots": [],
                    "date": "2025-10-28T00:00:00+02:00",
                    "status": "EmergencyShutdowns"
                },
                "updatedOn": "2025-10-27T07:04:31+00:00"
            }
        }
        """
        # DEBUG. DO NOT COMMIT UNCOMMENTED!

    def get_yasno_regions(self) -> list[dict]:
        """Get a list of available regions."""
        if not self.regions_data:
            return []

        return self.regions_data

    def get_region_by_name(self, region_name: str) -> dict | None:
        """Get region data by name."""
        for region in self.get_yasno_regions():
            if region["value"] == region_name:
                return region

        return None

    def get_yasno_providers_for_region(self, region_name: str) -> list[dict]:
        """Get providers for a specific region."""
        region = self.get_region_by_name(region_name)
        if not region:
            return []

        return region.get("dsos", [])

    def get_yasno_provider_by_name(
        self, region_name: str, provider_name: str
    ) -> dict | None:
        """Get provider data by region and provider name."""
        providers = self.get_yasno_providers_for_region(region_name)
        for provider in providers:
            if provider["name"] == provider_name:
                return provider

        return None

    def get_yasno_groups(self) -> list[str]:
        """Get groups from planned outage data."""
        if not self.planned_outage_data:
            return []

        return list(self.planned_outage_data.keys())

    def _get_group_data(self) -> dict | None:
        """
        Get data for the configured group.

        {
          'today': {
            'slots': [
              {
                'start': 0,
                'end': 1140,
                'type': 'NotPlanned'
              },
              {
                'start': 1140,
                'end': 1320,
                'type': 'Definite'
              },
              {
                'start': 1320,
                'end': 1440,
                'type': 'NotPlanned'
              }
            ],
            'date': '2025-10-28T00:00:00+02:00',
            'status': 'ScheduleApplies'
          },
          'tomorrow': {
            'slots': [
              {
                'start': 0,
                'end': 960,
                'type': 'NotPlanned'
              },
              {
                'start': 960,
                'end': 1200,
                'type': 'Definite'
              },
              {
                'start': 1200,
                'end': 1440,
                'type': 'NotPlanned'
              }
            ],
            'date': '2025-10-29T00:00:00+02:00',
            'status': 'WaitingForSchedule'
          },
          'updatedOn': '2025-10-28T10:23:56+00:00'
        }
        """
        if not self.planned_outage_data or self.group not in self.planned_outage_data:
            return None

        return self.planned_outage_data[self.group]

    def get_updated_on(self) -> datetime.datetime | None:
        """Get the updated on timestamp for the configured group."""
        group_data = self._get_group_data()
        if not group_data or "updatedOn" not in group_data:
            return None

        try:
            updated_on = dt_utils.parse_datetime(group_data["updatedOn"])
            if updated_on:
                return dt_utils.as_local(updated_on)
        except (ValueError, TypeError):
            LOGGER.warning(
                "Failed to parse updatedOn timestamp: %s",
                group_data["updatedOn"],
            )
            return None

    def get_current_event(self, at: datetime.datetime) -> PlannedOutageEvent | None:
        """Get the current event."""
        all_events = self.get_events(at, at + datetime.timedelta(days=1))
        for event in all_events:
            if event.all_day and event.start == at.date():
                return event
            if not event.all_day and event.start <= at < event.end:
                return event

        return None

    def get_events(
        self, start_date: datetime.datetime, end_date: datetime.datetime
    ) -> list[PlannedOutageEvent]:
        """Get all events within the date range."""
        group_data = self._get_group_data()
        if not group_data:
            return []

        LOGGER.debug("Group data for %s: %s", self.group, group_data)

        events = []
        for key, day_data in group_data.items():
            # parse only "today" and "tomorrow"
            if key == "updatedOn" or not isinstance(day_data, dict):
                continue

            date_str = day_data.get("date")
            if not date_str:
                continue

            day_dt = dt_utils.parse_datetime(date_str)
            if not day_dt:
                continue

            status = day_data.get(BLOCK_KEY_STATUS)
            if status == YasnoPlannedOutageDayStatus.STATUS_SCHEDULE_APPLIES.value:
                events.extend(_parse_day_schedule(day_data, day_dt))
            elif status == YasnoPlannedOutageDayStatus.STATUS_EMERGENCY_SHUTDOWNS.value:
                """
                {
                    "3.1": {
                        "today": {
                            "slots": [],
                            "date": "2025-10-27T00:00:00+02:00",
                            "status": "EmergencyShutdowns"
                        },
                        "tomorrow": {
                            "slots": [],
                            "date": "2025-10-28T00:00:00+02:00",
                            "status": "EmergencyShutdowns"
                        },
                        "updatedOn": "2025-10-27T07:04:31+00:00"
                    }
                }
                """
                events.append(
                    PlannedOutageEvent(
                        start=day_dt.date(),
                        end=day_dt.date(),
                        all_day=True,
                        event_type=PlannedOutageEventType.EMERGENCY,
                    )
                )

        events.sort(
            key=lambda e: (
                datetime.datetime.combine(e.start, datetime.time.min)
                if isinstance(e.start, datetime.date)
                else e.start
            )
        )

        return [
            e
            for e in events
            if e.all_day or not (e.end <= start_date or e.start >= end_date)
        ]

    async def fetch_data(self) -> None:
        """Fetch all required data."""
        await self.fetch_planned_outage_data()
