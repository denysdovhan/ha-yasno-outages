"""DTEK API client for Svitlo Yeah integration."""

from __future__ import annotations

import datetime
import json
import logging
import re

import aiohttp
from homeassistant.util import dt as dt_utils

from ..const import DTEK_HEADERS
from ..models import PlannedOutageEvent, PlannedOutageEventType

LOGGER = logging.getLogger(__name__)


def _parse_group_hours(
    group_hours: dict[str, str],
) -> list[tuple[datetime.time, datetime.time]]:
    """
    Parse group hours data into a list of outage time ranges.

    'GPV1.1': {
    '1': 'yes',
    ...
    '12': 'yes',
    '13': 'second',
    '14': 'no',
    '15': 'no',
    '16': 'no',
    '17': 'first',
    '18': 'yes',
    ...
    '24': 'yes',
    },
    """
    ranges = []
    outage_start = None

    for n in range(1, 25):  # 1 to 24
        hour = n - 1
        status = group_hours.get(str(n), "yes")

        if status == "yes":
            if outage_start is not None:
                ranges.append((outage_start, datetime.time(hour, 0)))
                outage_start = None
        else:  # "first", "no", or "second" - all are outages
            if outage_start is None:  # Start outage at appropriate time
                outage_start = (
                    datetime.time(hour, 30)
                    if status == "second"
                    else datetime.time(hour, 0)
                )
            if status == "first":  # If "first", close at hour:30 (next will be "yes")
                ranges.append((outage_start, datetime.time(hour, 30)))
                outage_start = None

    if outage_start is not None:
        ranges.append((outage_start, datetime.time(23, 59, 59)))

    return ranges


def _extract_data(html: str) -> dict | None:
    """Extract data from HTML."""
    pattern = r"DisconSchedule\.fact\s*=\s*({.*?})</script>"
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        LOGGER.error(
            "Could not find DisconSchedule.fact in HTML. "
            "This may indicate that the request is being filtered as bot "
            "or the service is down. If you are sure that the service is up, "
            "please create an issue."
        )
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        LOGGER.exception("Failed to parse DisconSchedule.fact JSON")
        return None


class DtekAPI:
    """Class to interact with DTEK Regions API."""

    _last_fetch: datetime.datetime | None = None
    _cached_data: dict | None = None

    def __init__(self, group: str | None = None) -> None:
        """Initialize the DTEK API."""
        self.group = group
        self.data = None

    async def fetch_data(self, cache_minutes: int = 15) -> None:
        """Fetch outage data from DTEK website."""
        now = datetime.datetime.now(datetime.UTC)
        if (
            DtekAPI._last_fetch
            and (now - DtekAPI._last_fetch).total_seconds() < cache_minutes * 60
        ):
            self.data = DtekAPI._cached_data
            return

        url = "https://www.dtek-krem.com.ua/ua/shutdowns"
        headers = DTEK_HEADERS
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
                )
                response.raise_for_status()
                self.data = _extract_data(await response.text())
                DtekAPI._cached_data = self.data
                DtekAPI._last_fetch = now
        except Exception:
            LOGGER.exception("Error fetching data from %s", url)
            self.data = None

    def get_dtek_region_groups(self) -> list[str]:
        """
        Get the list of available groups (with GPV prefix stripped).

        {
        'data': {
            '1761688800': {
                'GPV1.1': {
        """
        if not self.data or "data" not in self.data:
            return []

        first_timestamp = next(iter(self.data["data"].values()), {})
        return [key.replace("GPV", "") for key in first_timestamp]

    def get_current_event(self, at: datetime.datetime) -> PlannedOutageEvent | None:
        """Get the current event at a specific time."""
        events = self.get_events(at, at + datetime.timedelta(days=1))
        for event in events:
            if event.start <= at < event.end:
                return event
        return None

    def get_events(
        self, start_date: datetime.datetime, end_date: datetime.datetime
    ) -> list[PlannedOutageEvent]:
        """Get all events within the date range."""
        if not self.data or "data" not in self.data or not self.group:
            return []

        events = []
        group_key = f"GPV{self.group}"
        for timestamp_str, day_data in self.data["data"].items():
            if group_key not in day_data:
                continue

            day_dt = dt_utils.utc_from_timestamp(int(timestamp_str))
            day_dt = dt_utils.as_local(day_dt)

            group_hours = day_data[group_key]
            time_ranges = _parse_group_hours(group_hours)

            for start_time, end_time in time_ranges:
                event_start = day_dt.replace(
                    hour=start_time.hour,
                    minute=start_time.minute,
                    second=0,
                    microsecond=0,
                )
                event_end = day_dt.replace(
                    hour=end_time.hour,
                    minute=end_time.minute,
                    second=end_time.second,
                    microsecond=end_time.microsecond,
                )

                events.append(
                    PlannedOutageEvent(
                        start=event_start,
                        end=event_end,
                        event_type=PlannedOutageEventType.DEFINITE,
                    )
                )

        events.sort(key=lambda e: e.start)
        return [e for e in events if not (e.end <= start_date or e.start >= end_date)]

    def get_updated_on(self) -> datetime.datetime | None:
        """Get the updated on timestamp."""
        if not self.data or "update" not in self.data:
            return None

        try:
            update_str = self.data["update"]
            naive_dt = datetime.datetime.strptime(  # noqa: DTZ007
                update_str, "%d.%m.%Y %H:%M"
            )
            aware_dt = dt_utils.as_local(naive_dt)
        except (ValueError, TypeError):
            LOGGER.warning("Failed to parse update timestamp: %s", self.data["update"])
            return None

        return aware_dt
