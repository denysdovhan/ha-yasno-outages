"""API for Yasno outages."""

import datetime
import logging
from pathlib import Path

import recurring_ical_events
from icalendar import Calendar

from .const import CALENDAR_PATH

LOGGER = logging.getLogger(__name__)


class YasnoOutagesApi:
    """Class to interact with calendar files for Yasno outages."""

    def __init__(self, group: int) -> None:
        """Initialize the YasnoOutagesApi."""
        self.group = group
        self.calendar: recurring_ical_events.UnfoldableCalendar = None

    @property
    def calendar_path(self) -> Path:
        """Return the path to the ICS file."""
        return Path(__file__).parent / CALENDAR_PATH.format(group=self.group)

    def fetch_calendar(self) -> None:
        """Fetch outages from the ICS file."""
        with self.calendar_path.open() as file:
            ical = Calendar.from_ical(file.read())
            self.calendar = recurring_ical_events.of(ical)
        return self.calendar

    def get_current_event(self, at: datetime.datetime) -> dict:
        """Get the current event."""
        if not self.calendar:
            return None
        events_at = self.calendar.at(at)
        LOGGER.debug("Events at %s: %s", at, events_at)
        if not events_at:
            return None
        return events_at[0]  # return only the first event

    def get_events(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[dict]:
        """Get all events."""
        if not self.calendar:
            return []
        return self.calendar.between(start_date, end_date)
