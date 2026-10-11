"""Confirmed Sumy outage schedules from Alerts Energy."""

import logging
import re
from copy import deepcopy
from datetime import UTC, date, datetime, time, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.svitlo_yeah.api.common_tools import REQUEST_ERRORS
from custom_components.svitlo_yeah.const import (
    ALERTS_ENERGY_INITIATOR,
    ALERTS_ENERGY_URL,
    TZ_UA,
)
from custom_components.svitlo_yeah.models import (
    PlannedOutageEvent,
    PlannedOutageEventType,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)
SHUTDOWNS_URL = ALERTS_ENERGY_URL
SOURCE_FORMAT = "alerts_energy_sumy_v1"
SUMY_OPERATOR = ALERTS_ENERGY_INITIATOR
GROUP_FORMAT = re.compile(r"^[1-6]\.[12]$")
HOURS_PER_DAY = 24
HALF_HOUR = 30
UNKNOWN_CODE = 9
FULL_HOUR = 1
FIRST_HALF = 2
SECOND_HALF = 3
UNKNOWN_STATUSES = {"WaitingForSchedule", "EmergencyShutdowns"}


def _require(condition: object) -> None:
    """Reject a malformed answer before any of it is applied."""
    if not condition:
        message = "Invalid Alerts Energy schedule"
        raise ValueError(message)


def _timestamp(value: object) -> datetime:
    """Parse a source timestamp without inventing its timezone."""
    _require(isinstance(value, str))
    parsed = datetime.fromisoformat(str(value))
    _require(parsed.tzinfo is not None and parsed.utcoffset() is not None)
    return parsed


def _codes(value: object, *, allow_empty: bool = False) -> list[int]:
    """Validate an entire hourly array, including unknown-hour markers."""
    _require(isinstance(value, list))
    codes = list(value) if isinstance(value, list) else []
    _require(len(codes) == HOURS_PER_DAY or (allow_empty and not codes))
    _require(all(type(code) is int and code in {0, 1, 2, 3, 9} for code in codes))
    return codes


def _half_hour(day: date, hour: int, minute: int) -> list[dict[str, str]]:
    """Include each real occurrence of a local half hour across DST changes."""
    events = []
    for fold in (0, 1):
        start = datetime.combine(day, time(hour, minute, fold=fold), tzinfo=TZ_UA)
        utc_start = start.astimezone(UTC)
        roundtrip = utc_start.astimezone(TZ_UA)
        if roundtrip != start or roundtrip.fold != fold:
            # Missing spring times and a second fold of an ordinary hour do not exist.
            continue
        end = (utc_start + timedelta(minutes=HALF_HOUR)).astimezone(TZ_UA)
        events.append({"start": start.isoformat(), "end": end.isoformat()})
    return events


def _day(row: dict, key: str, expected_date: date) -> dict:
    """Normalize one dated schedule; an unknown day contains no events."""
    _require(row.get(f"{key}Date") == expected_date.isoformat())
    status = row.get(f"{key}Status")
    _require(status in {"ScheduleApplies", "NoShutdowns", *UNKNOWN_STATUSES})
    unknown = status in UNKNOWN_STATUSES
    codes = _codes(row.get(key), allow_empty=unknown)
    possible = _codes(row.get(f"{key}Possible", [0] * HOURS_PER_DAY), allow_empty=True)
    if status == "NoShutdowns":
        _require(not any(codes))
    unknown = unknown or UNKNOWN_CODE in codes
    events = []
    if not unknown:
        for hour, code in enumerate(codes):
            if code in {FULL_HOUR, FIRST_HALF}:
                events.extend(_half_hour(expected_date, hour, 0))
            if code in {FULL_HOUR, SECOND_HALF}:
                events.extend(_half_hour(expected_date, hour, HALF_HOUR))
    return {
        "date": expected_date.isoformat(),
        "complete": not unknown and not any(possible),
        "events": events,
    }


def _snapshot(row: dict, group: str, today: date) -> dict:
    """Validate both days and update time as a single answer."""
    return {
        "format": SOURCE_FORMAT,
        "group": group,
        "days": [
            _day(row, "today", today),
            _day(row, "tomorrow", today + timedelta(days=1)),
        ],
        "last_update": _timestamp(row.get("updated")).isoformat(),
    }


def _legacy_source(source: dict) -> dict:
    """Convert a kept E-Svitlo answer locally, preserving exact period boundaries."""
    answer = source["disconnections"]
    _require(isinstance(answer, dict) and isinstance(answer.get("data"), dict))
    data = answer["data"]
    days = []
    for section in (data, data.get("dict_tom", {})):
        _require(isinstance(section, dict))
        if not section.get("date_today"):
            continue
        day = datetime.strptime(section["date_today"], "%d.%m.%Y").date()  # noqa: DTZ007
        periods = section.get("lst_time_disc", [])
        _require(isinstance(periods, list))
        events = []
        for period in periods:
            _require(isinstance(period, dict))
            start = datetime.combine(
                day, time.fromisoformat(period["start_time"]), tzinfo=TZ_UA
            )
            end = datetime.combine(
                day, time.fromisoformat(period["end_time"]), tzinfo=TZ_UA
            )
            if end < start:
                end += timedelta(days=1)
            _require(start < end)
            events.append({"start": start.isoformat(), "end": end.isoformat()})
        days.append({"date": day.isoformat(), "complete": True, "events": events})
    return {
        "format": SOURCE_FORMAT,
        "group": source["group"],
        "days": days,
        "last_update": source.get("last_update"),
    }


class AlertsEnergyClient:
    """Fetch and retain confirmed schedules for one Sumy subgroup."""

    def __init__(self, hass: HomeAssistant, group: str | None = None) -> None:
        """Use Home Assistant's shared session without credentials."""
        self.session = async_get_clientsession(hass)
        self.group = group
        self.group_listed: bool | None = None
        self._groups: list[str] = []
        self._source: dict | None = None
        self._events: list[PlannedOutageEvent] = []
        self._last_update: datetime | None = None

    async def fetch_data(self) -> bool:
        """Apply a fully validated answer, retaining old data on failure."""
        today = datetime.now(TZ_UA).date()
        try:
            async with self.session.get(
                SHUTDOWNS_URL, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != HTTPStatus.OK:
                    LOGGER.debug("Alerts Energy HTTP error: %s", response.status)
                    return False
                rows = await response.json()
            _require(isinstance(rows, list))
            schedules = {}
            for row in rows:
                _require(isinstance(row, dict))
                if row.get("initiator") != SUMY_OPERATOR:
                    continue
                group = row.get("queue")
                _require(isinstance(group, str) and bool(GROUP_FORMAT.fullmatch(group)))
                _require(group not in schedules)
                schedules[group] = row
            _require(bool(schedules))
            if self.group is None:
                for group, row in schedules.items():
                    _snapshot(row, group, today)
            elif self.group not in schedules:
                self.group_listed = False
                return False
            else:
                source = _snapshot(schedules[self.group], self.group, today)
                self._apply_source(source)
                self.group_listed = True
            self._groups = sorted(schedules)
        except (*REQUEST_ERRORS, TypeError, KeyError):
            LOGGER.debug("Invalid or unavailable Alerts Energy answer", exc_info=True)
            return False
        return True

    def get_groups(self) -> list[str]:
        """Return the groups from the last valid answer."""
        return list(self._groups)

    def _apply_source(self, source: dict) -> None:
        """Validate kept data and merge only truly adjacent confirmed intervals."""
        _require(source.get("format") == SOURCE_FORMAT)
        _require(isinstance(source.get("days"), list))
        intervals = []
        dates = set()
        for day in source["days"]:
            _require(isinstance(day, dict))
            day_date = date.fromisoformat(day["date"])
            _require(day_date not in dates and type(day.get("complete")) is bool)
            dates.add(day_date)
            _require(isinstance(day.get("events"), list))
            for event in day["events"]:
                _require(isinstance(event, dict))
                start, end = _timestamp(event["start"]), _timestamp(event["end"])
                _require(start < end and start.astimezone(TZ_UA).date() == day_date)
                intervals.append((start, end))
        update = source.get("last_update")
        last_update = _timestamp(update) if update is not None else None
        merged: list[tuple[datetime, datetime]] = []
        for interval_start, interval_end in sorted(intervals):
            start, end = interval_start, interval_end
            if merged and merged[-1][1] >= interval_start:
                previous_start, previous_end = merged.pop()
                start, end = previous_start, max(previous_end, end)
            merged.append((start, end))
        self._source = deepcopy(source)
        self._events = [
            PlannedOutageEvent(PlannedOutageEventType.DEFINITE, start=start, end=end)
            for start, end in merged
        ]
        self._last_update = last_update

    def source_data(self) -> dict | None:
        """Return the serializable snapshot, without exposing mutable state."""
        return deepcopy(self._source)

    def restore_source_data(self, source: dict) -> None:
        """Restore only the configured group, without any HTTP requests."""
        if self.group is None or source.get("group") != self.group:
            return
        try:
            if "disconnections" in source:
                source = _legacy_source(source)
            self._apply_source(source)
        except ValueError, TypeError, KeyError:
            LOGGER.debug("Invalid kept Sumy schedule", exc_info=True)

    def has_complete_day(self, at: datetime) -> bool:
        """Return whether absence of an event means normal supply on this day."""
        if self._source is None:
            return False
        day_date = at.astimezone(TZ_UA).date().isoformat()
        return any(
            day["date"] == day_date and day["complete"] for day in self._source["days"]
        )

    def get_current_event(self, at: datetime) -> PlannedOutageEvent | None:
        """Return the confirmed interval containing this moment."""
        return next(
            (event for event in self._events if event.start <= at < event.end), None
        )

    def get_events(self, start: datetime, end: datetime) -> list[PlannedOutageEvent]:
        """Return confirmed intervals that overlap the requested range."""
        return [
            event for event in self._events if event.end > start and event.start < end
        ]

    def get_updated_on(self) -> datetime | None:
        """Return the source timestamp, never the request time."""
        return self._last_update
