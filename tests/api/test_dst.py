"""Timezone and daylight saving regression tests."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.yasno_outages.api import YasnoApi
from custom_components.yasno_outages.api.base import BaseYasnoApi
from custom_components.yasno_outages.api.models import OutageEventType

KYIV = ZoneInfo("Europe/Kyiv")


@pytest.fixture(params=["planned", "probable"])
def dst_api(request):
    api = YasnoApi(25, 902, "3.1")
    slots = [
        {"start": 120, "end": 210, "type": "Definite"},
        {"start": 210, "end": 240, "type": "NotPlanned"},
    ]
    api.planned.planned_outages_data = {
        "3.1": {"today": {"date": "2026-10-25T00:00:00+03:00", "slots": slots}}
    }
    api.probable.probable_outages_data = {
        "25": {"dsos": {"902": {"groups": {"3.1": {"slots": {"6": slots}}}}}}
    }
    return getattr(api, request.param)


@pytest.mark.parametrize(
    ("schedule_date", "minutes", "expected"),
    [
        ("2026-01-15T00:00:00+03:00", 480, "2026-01-15T08:00:00+02:00"),
        ("2026-07-15T00:00:00+03:00", 480, "2026-07-15T08:00:00+03:00"),
        ("2026-03-29T00:00:00+02:00", 480, "2026-03-29T08:00:00+03:00"),
        ("2026-10-25T00:00:00+03:00", 480, "2026-10-25T08:00:00+02:00"),
        ("2026-03-29T00:00:00+02:00", 1440, "2026-03-30T00:00:00+03:00"),
        ("2026-10-25T00:00:00+03:00", 1440, "2026-10-26T00:00:00+02:00"),
    ],
)
def test_minutes_to_time_uses_kyiv_offset(schedule_date, minutes, expected):
    result = BaseYasnoApi.minutes_to_time(
        minutes, datetime.fromisoformat(schedule_date)
    )
    assert result.isoformat() == expected


@pytest.mark.parametrize("query_tz", [KYIV, UTC])
@pytest.mark.parametrize(
    ("fold", "expected_type"),
    [(0, OutageEventType.DEFINITE), (1, OutageEventType.NOT_PLANNED)],
)
def test_current_event_distinguishes_repeated_hour(
    dst_api, query_tz, fold, expected_type
):
    at = datetime(2026, 10, 25, 3, 15, tzinfo=KYIV, fold=fold).astimezone(query_tz)
    event = dst_api.get_current_event(at)
    assert event is not None
    assert event.event_type == expected_type
    assert event.start.timestamp() <= at.timestamp() < event.end.timestamp()


@pytest.mark.parametrize("query_tz", [KYIV, UTC])
def test_event_range_excludes_outage_from_first_hour(dst_api, query_tz):
    start = datetime(2026, 10, 25, 3, 15, tzinfo=KYIV, fold=1)
    end = datetime(2026, 10, 25, 3, 20, tzinfo=KYIV, fold=1)
    events = dst_api.get_events_between(
        start.astimezone(query_tz), end.astimezone(query_tz)
    )
    assert len(events) == 1
    assert events[0].event_type == OutageEventType.NOT_PLANNED


def test_next_event_skips_event_started_in_first_hour(dst_api):
    at = datetime(2026, 10, 25, 3, 15, tzinfo=KYIV, fold=1)
    assert dst_api.get_next_event(at, event_type=OutageEventType.NOT_PLANNED) is None


def test_current_event_uses_kyiv_date_for_utc_query(dst_api):
    at = datetime(2026, 10, 24, 23, 15, tzinfo=UTC)
    event = dst_api.get_current_event(at)
    assert event is not None
    assert event.event_type == OutageEventType.DEFINITE
    assert event.start.date() == at.astimezone(KYIV).date()


def test_naive_queries_use_kyiv_time(dst_api):
    at = datetime(2026, 10, 25, 3, 15)
    event = dst_api.get_current_event(at)
    assert event is not None
    assert event.event_type == OutageEventType.DEFINITE
    events = dst_api.get_events_between(at, at.replace(minute=20))
    assert len(events) == 1
    assert events[0].event_type == OutageEventType.DEFINITE
    next_event = dst_api.get_next_event(at, event_type=OutageEventType.NOT_PLANNED)
    assert next_event is not None
    assert next_event.start.isoformat() == "2026-10-25T03:30:00+03:00"


def test_weekly_recurrence_changes_offset_after_dst():
    api = YasnoApi(25, 902, "3.1").probable
    api.probable_outages_data = {
        "25": {
            "dsos": {
                "902": {
                    "groups": {
                        "3.1": {
                            "slots": {
                                "6": [{"start": 480, "end": 720, "type": "Definite"}]
                            }
                        }
                    }
                }
            }
        }
    }
    start = datetime(2026, 10, 18, tzinfo=KYIV)
    events = api.get_events_between(start, start + timedelta(days=8))
    assert [event.start.isoformat() for event in events] == [
        "2026-10-18T08:00:00+03:00",
        "2026-10-25T08:00:00+02:00",
    ]
