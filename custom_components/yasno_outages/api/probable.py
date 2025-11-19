"""Probable outages API for Yasno."""

import datetime
import logging

import aiohttp
from dateutil.rrule import WEEKLY, rrule

from .base import BaseYasnoApi
from .const import PROBABLE_OUTAGES_ENDPOINT
from .models import OutageEvent, OutageSlot, OutageSource

LOGGER = logging.getLogger(__name__)


class ProbableOutagesApi(BaseYasnoApi):
    """API for fetching probable outages data."""

    def __init__(
        self,
        region_id: int | None = None,
        provider_id: int | None = None,
        group: str | None = None,
    ) -> None:
        """Initialize the ProbableOutagesApi."""
        super().__init__(region_id, provider_id, group)
        self.probable_outages_data = None

    async def fetch_probable_outages_data(self) -> None:
        """Fetch probable outages data for the configured region and provider."""
        if not self.region_id or not self.provider_id:
            LOGGER.warning(
                "Region and Provider ID must be set before fetching probable outages",
            )
            return

        url = PROBABLE_OUTAGES_ENDPOINT.format(
            region_id=self.region_id,
            dso_id=self.provider_id,
        )

        async with aiohttp.ClientSession() as session:
            self.probable_outages_data = await self._get_data(session, url)

    def get_probable_slots_for_weekday(
        self,
        weekday: int,
    ) -> list[OutageSlot]:
        """Get probable outage slots for a specific weekday."""
        if not self.probable_outages_data:
            return []

        region_data = self.probable_outages_data.get(str(self.region_id), {})
        dsos_data = region_data.get("dsos", {})
        dso_data = dsos_data.get(str(self.provider_id), {})
        groups_data = dso_data.get("groups", {})
        group_data = groups_data.get(self.group, {})
        slots_data = group_data.get("slots", {})
        weekday_slots = slots_data.get(str(weekday), [])

        return self._parse_raw_slots(weekday_slots)

    def get_current_event(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the probable outage event at a given time."""
        weekday = at.weekday()  # 0=Monday, 6=Sunday
        slots = self.get_probable_slots_for_weekday(weekday)

        # Find slot that contains the current time
        minutes_since_midnight = at.hour * 60 + at.minute

        for slot in slots:
            if slot.start <= minutes_since_midnight < slot.end:
                # Found matching slot, create event for today
                date = at.replace(hour=0, minute=0, second=0, microsecond=0)
                event_start = self.minutes_to_time(slot.start, date)
                event_end = self.minutes_to_time(slot.end, date)

                return OutageEvent(
                    start=event_start,
                    end=event_end,
                    event_type=slot.event_type,
                    source=OutageSource.PROBABLE,
                )

        return None

    def get_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get all probable outage events within the date range using rrule."""
        events = []

        # Iterate through each day of the week (0=Monday, 6=Sunday)
        for weekday in range(7):
            slots = self.get_probable_slots_for_weekday(weekday)

            for slot in slots:
                # Find the first occurrence of this weekday >= start_date
                days_ahead = weekday - start_date.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                first_occurrence = start_date + datetime.timedelta(days=days_ahead)
                first_occurrence = first_occurrence.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

                # Generate recurring events for this slot using rrule
                # WEEKLY recurrence for this specific weekday
                for dt in rrule(
                    freq=WEEKLY,
                    dtstart=first_occurrence,
                    until=end_date,
                    byweekday=weekday,
                ):
                    event_start = self.minutes_to_time(slot.start, dt)
                    event_end = self.minutes_to_time(slot.end, dt)

                    # Skip if event is completely outside the requested range
                    if event_end < start_date or event_start > end_date:
                        continue

                    events.append(
                        OutageEvent(
                            start=event_start,
                            end=event_end,
                            event_type=slot.event_type,
                            source=OutageSource.PROBABLE,
                        )
                    )

        # Sort by start time
        return sorted(events, key=lambda e: e.start)

    async def fetch_data(self) -> None:
        """Fetch all required data."""
        await self.fetch_probable_outages_data()
