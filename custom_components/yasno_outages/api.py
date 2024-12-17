"""API for Yasno outages."""

import datetime
import logging

import requests
from dateutil.rrule import WEEKLY, rrule

LOGGER = logging.getLogger(__name__)

API_ENDPOINT = (
    "https://api.yasno.com.ua/api/v1/pages/home/schedule-turn-off-electricity"
)
START_OF_DAY = 0
END_OF_DAY = 24


class YasnoOutagesApi:
    """Class to interact with Yasno outages API."""

    """Group name format"""
    group_name = "group_{group}"

    def __init__(self, city: str | None = None, group: str | None = None) -> None:
        """Initialize the YasnoOutagesApi."""
        self.group = group
        self.city = city
        self.api_url = API_ENDPOINT
        self.schedule = None

    def _merge_intervals(self, intervals: list) -> list:
        if not intervals:
            return []

        merged = [intervals[0]]
        for current in intervals[1:]:
            previous = merged[-1]
            if (
                previous["end"] == current["start"]
                and previous["type"] == current["type"]
            ):
                previous["end"] = current["end"]
            else:
                merged.append(current)
        return merged

    def _get_weekday_from_day_name(self, day_name: str) -> str:
        date = {
            "today": datetime.datetime.today(),  # noqa: DTZ002
            "tomorrow": datetime.datetime.today() + datetime.timedelta(days=1),  # noqa: DTZ002
        }
        dow = date.get(day_name)
        return dow.weekday() if dow else None

    def _extract_daily_schedule(self, response_data: dict) -> dict:
        data = response_data.get("dailySchedule")

        if not data:
            return {}

        schedule = {}
        for city, day_data in data.items():
            if city not in schedule:
                schedule[city] = {}
            for day, details in day_data.items():
                weekday = self._get_weekday_from_day_name(day)
                for group, intervals in details.get("groups", {}).items():
                    if group not in schedule[city]:
                        schedule[city][group] = {}
                    if weekday not in schedule[city][group]:
                        schedule[city][group][weekday] = self._merge_intervals(
                            sorted(intervals, key=lambda x: x["start"]),
                        )

        return schedule

    def _extract_weekly_schedule(self, response_data: dict) -> dict:
        data = response_data.get("schedule", {})

        if not data:
            return {}

        schedule = {}
        for city, groups in data.items():
            if city not in schedule:
                schedule[city] = {}
            for group, weekly_schedule in groups.items():
                group_name = str(group[len("group_") :])
                if group_name not in schedule[city]:
                    schedule[city][group_name] = {}
                for weekday, intervals in enumerate(weekly_schedule):
                    if weekday not in schedule[city][group_name]:
                        schedule[city][group_name][weekday] = {}
                    schedule[city][group_name][weekday] = self._merge_intervals(
                        sorted(intervals, key=lambda x: x["start"]),
                    )

        return schedule

    def _merge_schedules(self, weekly_schedule: dict, daily_schedule: dict) -> dict:
        merged = {}

        for city in weekly_schedule.keys() | daily_schedule.keys():
            merged[city] = {}

            weekly_groups = weekly_schedule.get(city, {})
            daily_groups = daily_schedule.get(city, {})

            for group in weekly_groups.keys() | daily_groups.keys():
                merged[city][group] = {}

                weekly_days = weekly_groups.get(group, {})
                daily_days = daily_groups.get(group, {})

                for weekday in weekly_days.keys() | daily_days.keys():
                    merged[city][group][weekday] = {}

                    weekly_intervals = weekly_days.get(weekday, [])
                    daily_intervals = daily_days.get(weekday, [])

                    merged[city][group][weekday] = weekly_intervals + daily_intervals

        return merged

    def _extract_schedule(self, data: dict) -> dict | None:
        """Extract schedule from the API response."""
        schedule_component = next(
            (
                item
                for item in data["components"]
                if item["template_name"] == "electricity-outages-daily-schedule"
            ),
            None,
        )

        if not schedule_component:
            LOGGER.error("Schedule component not found in the API response.")
            return None

        weekly_schedule = self._extract_weekly_schedule(schedule_component)
        daily_schedule = self._extract_daily_schedule(schedule_component)

        return self._merge_schedules(weekly_schedule, daily_schedule)

    def _build_event_hour(
        self,
        date: datetime.datetime,
        start_hour: int,
    ) -> datetime.datetime:
        hour = int(start_hour)
        minute = int((start_hour - hour) * 60)
        return date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def fetch_schedule(self) -> None:
        """Fetch outages from the API."""
        try:
            response = requests.get(self.api_url, timeout=60)
            response.raise_for_status()
            self.schedule = self._extract_schedule(response.json())
        except requests.RequestException as error:
            LOGGER.exception("Error fetching schedule from Yasno API: %s", error)  # noqa: TRY401
            self.schedule = {}

    def get_cities(self) -> list[str]:
        """Get a list of available cities."""
        return list(self.schedule.keys()) if self.schedule else []

    def get_city_groups(self, city: str) -> dict[str, list]:
        """Get all schedules for all of available groups for a city."""
        return self.schedule.get(city, {}) if self.schedule else {}

    def get_group_schedule(self, city: str, group: str) -> list:
        """Get the schedule for a specific group."""
        city_groups = self.get_city_groups(city)
        return city_groups.get(group, [])

    def get_current_event(self, at: datetime.datetime) -> dict | None:
        """Get the current event."""
        for event in self.get_events(at, at + datetime.timedelta(days=1)):
            if event["start"] <= at < event["end"]:
                return event
        return None

    def get_events(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[dict]:
        """Get all events."""
        if not self.city or not self.group:
            return []

        group_schedule = self.get_group_schedule(self.city, self.group)

        if not group_schedule:
            return []

        events = []
        # For each day of the week in the schedule
        for weekday, intervals in group_schedule.items():
            # Build a recurrence rule the events between start and end dates
            recurrance_rule = rrule(
                WEEKLY,
                dtstart=start_date,
                until=end_date,
                byweekday=weekday,
            )

            # For each event in the day
            for event in intervals:
                event_start_hour = event["start"]
                event_end_hour = event["end"]

                if event_end_hour == END_OF_DAY:
                    event_end_hour = START_OF_DAY

                # For each date in the recurrence rule
                for dt in recurrance_rule:
                    event_start = self._build_event_hour(dt, event_start_hour)
                    event_end = self._build_event_hour(dt, event_end_hour)
                    if event_end_hour == START_OF_DAY:
                        event_end += datetime.timedelta(days=1)
                    if (
                        start_date <= event_start <= end_date
                        or start_date <= event_end <= end_date
                        # Include events that intersect beyond the timeframe
                        # See: https://github.com/denysdovhan/ha-yasno-outages/issues/14
                        or event_start <= start_date <= event_end
                        or event_start <= end_date <= event_end
                    ):
                        events.append(
                            {
                                "summary": event["type"],
                                "start": event_start,
                                "end": event_end,
                            },
                        )

        # Sort events by start time to ensure correct order
        return sorted(events, key=lambda event: event["start"])
