"""API for Yasno outages."""

import datetime
import logging
import requests
import re
import heapq
from typing import Any, Generator, Optional

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
        self.daily_schedule = None

    def _extract_data_from_api_response(self, data: dict) -> None:
        """Extract schedule from the API response."""
        schedule_component = next(
            (
                item
                for item in data["components"]
                if item["template_name"] == "electricity-outages-schedule"
            ),
            None,
        )
        daily_schedule_component = next(
            (
                item
                for item in data["components"]
                if item["template_name"] == "electricity-outages-daily-schedule"
            ),
            None,
        )
        if schedule_component and "schedule" in schedule_component:
            self.schedule = schedule_component["schedule"]
        else:
            LOGGER.error("Schedule component not found in the API response.")
        if daily_schedule_component and "dailySchedule" in daily_schedule_component:
            self.daily_schedule = daily_schedule_component["dailySchedule"]
        else:
            LOGGER.warning("Daily schedule component not found in the API response.")

    def _build_event_hour(
        self,
        date: datetime.datetime,
        start_hour: float,
    ) -> datetime.datetime:
        if start_hour == END_OF_DAY:
            start_hour = START_OF_DAY
            date = date + datetime.timedelta(days=1)
        hour = int(start_hour // 1)
        minute = int((start_hour % 1) * 60)
        return date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def fetch_schedule(self) -> None:
        """Fetch outages from the API."""
        try:
            response = requests.get(self.api_url, timeout=60)
            response.raise_for_status()
            self._extract_data_from_api_response(response.json())
        except requests.RequestException as error:
            LOGGER.exception("Error fetching schedule from Yasno API: %s", error)  # noqa: TRY401
            self.schedule = {}

    def get_cities(self) -> list[str]:
        """Get a list of available cities."""
        return (
            list(self.schedule.keys())
            if self.schedule
            else list(self.daily_schedule.keys())
            if self.daily_schedule
            else []
        )

    def get_city_groups(self, city: str) -> dict[str, list]:
        """Get all schedules for all of available groups for a city."""
        if self.schedule:
            return self.schedule.get(city, {})
        if self.daily_schedule:
            city_groups = {}
            for day, details in self.daily_schedule.get(city, {}).items():
                for group, intervals in details.get("groups", {}).items():
                    if self.group_name.format(group=group) not in city_groups:
                        city_groups[self.group_name.format(group=group)] = {}
            return city_groups 
        return {} 

    def get_group_schedule(self, city: str, group: str) -> list:
        """Get the schedule for a specific group."""
        city_groups = self.get_city_groups(city)
        return city_groups.get(self.group_name.format(group=group), [])

    def get_current_event(self, at: datetime.datetime) -> dict | None:
        """Get the current event."""
        for event in self.gen_events(at, at + datetime.timedelta(days = 1)):
            if event["start"] <= at < event["end"]:
                return event
        return None

    def gen_event(self, base_date: datetime.datetime, event: Any, priority: int=1):
        yield {
            "at": self._build_event_hour(base_date, event["start"]),
            "priority": priority,
            "action": "open",
            "type": event["type"],
        }
        yield {
            "at": self._build_event_hour(base_date, event["end"]),
            "priority": priority,
            "action": "close",
            "type": event["type"],
        }

    def gen_schedule_recurrent_events(
        self, start_date: datetime.datetime
    ) -> Generator[Any, Any, Any]:
        """Generate schedule recurrent events."""
        if not self.city or not self.group:
            return []

        group_schedule = self.get_group_schedule(self.city, self.group)
        if not group_schedule:
            return []

        cday = start_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - datetime.timedelta(days=start_date.weekday())

        while True:
            # For each day of the week in the schedule
            for day_events in group_schedule:
                # For each event in the day
                for event in day_events:
                    yield from self.gen_event(cday, event)

                cday += datetime.timedelta(days=1)

    def gen_exception_events(self, base_date: datetime.datetime) -> Generator[any, any, any]:
        if self.daily_schedule is None:
            return
        result = []
        city_exceptions = self.daily_schedule[self.city]
        for ex in city_exceptions.values():
            match = re.search(r'(\d+)\.(\d+)\.(\d+)', ex['title'])
            if match is None:
                LOGGER.warning(f'no date match found in "{ex['title']}"')
                continue
            y, m, d = int(match.group(3)), int(match.group(2)), int(match.group(1))
            day_date = base_date.replace(year=y, month=m, day=d)
            yield {
                "at": self._build_event_hour(day_date, 0),
                "priority": 2,
                "action": "open",
                "type": "none",
            }
            for event in ex['groups'][self.group]:
                yield from self.gen_event(base_date=day_date, event=event, priority=3)
            yield {
                "at": self._build_event_hour(day_date, 24),
                "priority": 2,
                "action": "close",
                "type": "none",
            }
        return result

    def gen_events(
        self,
        start_date: datetime.datetime,
        end_date: Optional[datetime.datetime]=None,
    ):
        """Generate all events."""

        stack = []
        now = None

        for ev in heapq.merge(
            self.gen_schedule_recurrent_events(start_date=start_date),
            self.gen_exception_events(base_date=start_date),
            key=lambda ev: (ev['at'], ev['priority'] if ev['action'] == 'close' else -ev['priority']),
        ):
            at, priority, action, t = ev['at'], ev['priority'], ev['action'], ev['type']
            if now is None:
                now = at

            if action == 'open':
                while len(stack) > priority:
                    last = stack[-1]
                    if last is None:
                        stack.pop()
                        continue
                    if "end" not in last:
                        break
                    stack.pop()
                    if last["end"] > now:
                        if last["summary"] != "none":
                            res = { **last, "start": now }
                            if res['end'] > start_date:
                                yield res
                        now = last["end"]
                        if end_date is not None and now > end_date:
                            return

                if priority < len(stack):
                    continue

                last = stack[-1] if len(stack) > 0 else None
                if last is None or last["summary"] != t or ("end" in last and last["end"] < at):
                    if last is not None:
                        s = max(now, last["start"])
                        if last["summary"] != "none" and ("end" not in last or last["end"] > now):
                            res = { "end": at, **last, "start": s }
                            if res['end'] > start_date:
                                yield res
                        now = at
                        if end_date is not None and now > end_date:
                            return

                    for _ in range(priority - len(stack)): stack.append(None)
                    stack = stack[0:priority-1] + [{ "summary": t, "start": at }]
                else:
                    for _ in range(priority - len(stack)): stack.append(None)
                    new_last = { **last }
                    del new_last['end']
                    stack = stack[0:priority-1] + [new_last]

            else:
                if priority <= len(stack) and stack[priority-1] is not None:
                    stack[priority-1]['end'] = at

        while len(stack) > 0:
            last = stack.pop()
            if last is None:
                continue
            if last["end"] > now:
                if last["summary"] != "none":
                    res = { **last, "start": now }
                    if res['end'] > start_date:
                        yield res
                now = last["end"]
                if end_date is not None and now > end_date:
                    return

    def get_events(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[dict]:
        """Get all events."""
        return [*self.gen_events(start_date=start_date, end_date=end_date)]
