"""Tests for Planned Outages API."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.yasno_outages.api.models import (
    OutageEventType,
    OutageSource,
    YasnoApiError,
)
from custom_components.yasno_outages.api.planned import PlannedOutagesApi

TEST_REGION_ID = 25
TEST_PROVIDER_ID = 902
TEST_GROUP = "3.1"


@pytest.fixture(name="api")
def _api():
    """Create an API instance."""
    return PlannedOutagesApi(
        region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP
    )


class TestPlannedOutagesApiInit:
    """Test PlannedOutagesApi initialization."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        api = PlannedOutagesApi(
            region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP
        )
        assert api.region_id == TEST_REGION_ID
        assert api.provider_id == TEST_PROVIDER_ID
        assert api.group == TEST_GROUP
        assert api.planned_outages_data is None

    def test_init_without_params(self):
        """Test initialization without parameters."""
        api = PlannedOutagesApi()
        assert api.region_id is None
        assert api.provider_id is None
        assert api.group is None


class TestPlannedOutagesApiFetchData:
    """Test data fetching methods."""

    async def test_fetch_planned_outages_success(self, api, planned_outage_data):
        """Test successful planned outage fetch."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=planned_outage_data)
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value.__aenter__.return_value = mock_response

            await api.fetch_planned_outages_data()
            assert api.planned_outages_data == planned_outage_data

    async def test_fetch_planned_outages_no_config(self):
        """Test planned outage fetch without region/provider."""
        api = PlannedOutagesApi()
        await api.fetch_planned_outages_data()
        assert api.planned_outages_data is None

    async def test_fetch_planned_outages_error(self, api):
        """Test planned outage fetch with error raises YasnoApiError."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.side_effect = aiohttp.ClientError()
            with pytest.raises(YasnoApiError):
                await api.fetch_planned_outages_data()

    async def test_fetch_data(self, api, planned_outage_data):
        """Test fetch_data method."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=planned_outage_data)
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value.__aenter__.return_value = mock_response

            await api.fetch_data()
            assert api.planned_outages_data == planned_outage_data


class TestPlannedOutagesApiGroups:
    """Test group-related methods."""

    def test_get_groups(self, api, planned_outage_data):
        """Test getting groups list."""
        api.planned_outages_data = planned_outage_data
        assert api.get_groups() == [TEST_GROUP]

    def test_get_groups_empty(self, api):
        """Test getting groups when none loaded."""
        assert api.get_groups() == []

    def test_get_planned_outages_data(self, api, planned_outage_data):
        """Test getting data for configured group."""
        api.planned_outages_data = planned_outage_data
        group_data = api.get_planned_outages_data()
        assert group_data is not None
        assert "today" in group_data
        assert "tomorrow" in group_data

    def test_get_planned_outages_data_no_data(self, api):
        """Test getting data when none loaded."""
        assert api.get_planned_outages_data() is None

    def test_get_planned_outages_data_wrong_group(self, api, planned_outage_data):
        """Test getting data for non-existent group."""
        api.planned_outages_data = planned_outage_data
        api.group = "99.9"
        assert api.get_planned_outages_data() is None


class TestPlannedOutagesApiDates:
    """Test date-related methods."""

    def test_get_planned_dates(self, api, planned_outage_data, today, tomorrow):
        """Test getting planned dates."""
        api.planned_outages_data = planned_outage_data
        dates = api.get_planned_dates()
        assert len(dates) == 2
        assert today.date() in dates
        assert tomorrow.date() in dates

    def test_get_planned_dates_no_data(self, api):
        """Test getting dates when no data."""
        assert api.get_planned_dates() == []

    def test_get_today_date(self, api, planned_outage_data, today):
        """Test getting today's date."""
        api.planned_outages_data = planned_outage_data
        today_date = api.get_today_date()
        assert today_date == today.date()

    def test_get_tomorrow_date(self, api, planned_outage_data, tomorrow):
        """Test getting tomorrow's date."""
        api.planned_outages_data = planned_outage_data
        tomorrow_date = api.get_tomorrow_date()
        assert tomorrow_date == tomorrow.date()

    def test_get_date_by_day_today(self, api, planned_outage_data, today):
        """Test getting date by day key."""
        api.planned_outages_data = planned_outage_data
        date = api.get_date_by_day("today")
        assert date == today.date()

    def test_get_date_by_day_no_data(self, api):
        """Test getting date when no data."""
        assert api.get_date_by_day("today") is None


class TestPlannedOutagesApiStatus:
    """Test status-related methods."""

    def test_get_status_today(self, api, planned_outage_data):
        """Test getting today's status."""
        api.planned_outages_data = planned_outage_data
        status = api.get_status_today()
        assert status == "ScheduleApplies"

    def test_get_status_tomorrow(self, api, planned_outage_data):
        """Test getting tomorrow's status."""
        api.planned_outages_data = planned_outage_data
        status = api.get_status_tomorrow()
        assert status == "ScheduleApplies"

    def test_get_status_by_day(self, api, planned_outage_data):
        """Test getting status by day key."""
        api.planned_outages_data = planned_outage_data
        status = api.get_status_by_day("today")
        assert status == "ScheduleApplies"

    def test_get_status_no_data(self, api):
        """Test getting status when no data."""
        assert api.get_status_today() is None

    def test_get_data_by_day(self, api, planned_outage_data):
        """Test getting data by day."""
        api.planned_outages_data = planned_outage_data
        day_data = api.get_data_by_day("today")
        assert day_data is not None
        assert "slots" in day_data
        assert "status" in day_data


class TestPlannedOutagesApiScheduleParsing:
    """Test schedule parsing methods."""

    def test_parse_day_schedule(self, api, today):
        """Test parsing day schedule."""
        day_data = {
            "slots": [
                {"start": 960, "end": 1200, "type": "Definite"},
                {"start": 1200, "end": 1440, "type": "NotPlanned"},
            ],
            "date": today.isoformat(),
        }
        events = api._parse_day_schedule(day_data, today)
        assert len(events) == 2
        assert events[0].event_type == OutageEventType.DEFINITE
        assert events[0].source == OutageSource.PLANNED
        assert events[0].start.hour == 16

    def test_parse_day_schedule_empty_slots(self, api, today):
        """Test parsing day schedule with empty slots."""
        day_data = {
            "slots": [],
            "date": today.isoformat(),
        }
        events = api._parse_day_schedule(day_data, today)
        assert len(events) == 0

    def test_parse_day_events(self, api, planned_outage_data):
        """Test parsing day events from group data."""
        api.planned_outages_data = planned_outage_data
        group_data = api.get_planned_outages_data()
        events = api._parse_day_events(group_data, "today")
        assert len(events) == 3

    def test_parse_day_events_no_day(self, api, planned_outage_data):
        """Test parsing day events when day key missing."""
        api.planned_outages_data = planned_outage_data
        group_data = api.get_planned_outages_data()
        events = api._parse_day_events(group_data, "next_week")
        assert len(events) == 0


class TestPlannedOutagesApiUpdatedOn:
    """Test updated on timestamp methods."""

    def test_get_updated_on(self, api, planned_outage_data):
        """Test getting updated timestamp."""
        api.planned_outages_data = planned_outage_data
        updated = api.get_updated_on()
        assert updated is not None

    def test_get_updated_on_no_data(self, api):
        """Test getting updated timestamp without data."""
        assert api.get_updated_on() is None


class TestPlannedOutagesApiEvents:
    """Test event retrieval methods."""

    def test_get_events_between(self, api, planned_outage_data, today, tomorrow):
        """Test getting events within date range."""
        api.planned_outages_data = planned_outage_data
        events = api.get_events_between(today, tomorrow.replace(hour=23, minute=59))
        # Should have 2 Definite events from the test data
        definite_events = [
            e for e in events if e.event_type == OutageEventType.DEFINITE
        ]
        assert len(definite_events) == 2

    def test_get_events_between_no_data(self, api, today, tomorrow):
        """Test getting events when no data."""
        events = api.get_events_between(today, tomorrow)
        assert events == []

    def test_get_events_between_wrong_group(
        self, api, planned_outage_data, today, tomorrow
    ):
        """Test getting events for wrong group."""
        api.planned_outages_data = planned_outage_data
        api.group = "99.9"
        events = api.get_events_between(today, tomorrow)
        assert events == []

    def test_get_events_between_filtered(self, api, planned_outage_data, today):
        """Test that events are filtered by date range."""
        api.planned_outages_data = planned_outage_data
        # Request only first hour of today
        events = api.get_events_between(today, today.replace(hour=1))
        # Should only get NotPlanned event that starts at midnight
        assert len(events) >= 1

    def test_get_current_event(self, api, planned_outage_data, today):
        """Test getting current event."""
        api.planned_outages_data = planned_outage_data
        # 17:00 should be in the Definite event (16:00-20:00 / 960-1200 minutes)
        at = today.replace(hour=17)
        event = api.get_current_event(at)
        assert event is not None
        assert event.event_type == OutageEventType.DEFINITE

    def test_get_current_event_none(self, api, planned_outage_data, today):
        """Test getting current event when none active."""
        api.planned_outages_data = planned_outage_data
        # 8:00 should be in NotPlanned period
        at = today.replace(hour=8)
        event = api.get_current_event(at)
        # Event exists but is NOT_PLANNED type
        if event:
            assert event.event_type == OutageEventType.NOT_PLANNED

    def test_get_current_event_no_data(self, api, today):
        """Test getting current event with no data."""
        event = api.get_current_event(today)
        assert event is None


class TestPlannedOutagesApiEdgeCases:
    """Test edge cases and special scenarios."""

    def test_midnight_spanning_events(self, api, today, tomorrow):
        """Test events that span across midnight."""
        api.planned_outages_data = {
            TEST_GROUP: {
                "today": {
                    "slots": [
                        {"start": 0, "end": 1320, "type": "NotPlanned"},  # 00:00-22:00
                        {"start": 1320, "end": 1440, "type": "Definite"},  # 22:00-24:00
                    ],
                    "date": today.isoformat(),
                    "status": "ScheduleApplies",
                },
                "tomorrow": {
                    "slots": [
                        {"start": 0, "end": 120, "type": "Definite"},  # 00:00-02:00
                        {"start": 120, "end": 1440, "type": "NotPlanned"},
                    ],
                    "date": tomorrow.isoformat(),
                    "status": "ScheduleApplies",
                },
                "updatedOn": today.isoformat(),
            }
        }

        events = api.get_events_between(today, tomorrow + datetime.timedelta(days=1))
        # Find the Definite events
        definite_events = [
            e for e in events if e.event_type == OutageEventType.DEFINITE
        ]
        assert len(definite_events) == 2

        # Verify times
        evening_event = [e for e in definite_events if e.start.hour == 22]
        morning_event = [e for e in definite_events if e.start.hour == 0]
        assert len(evening_event) == 1
        assert len(morning_event) == 1

    def test_event_at_midnight(self, api, today, tomorrow):
        """Test getting event exactly at midnight."""
        api.planned_outages_data = {
            TEST_GROUP: {
                "today": {
                    "slots": [
                        {"start": 1320, "end": 1440, "type": "Definite"},
                    ],
                    "date": today.isoformat(),
                    "status": "ScheduleApplies",
                },
                "tomorrow": {
                    "slots": [
                        {"start": 0, "end": 120, "type": "Definite"},
                    ],
                    "date": tomorrow.isoformat(),
                    "status": "ScheduleApplies",
                },
                "updatedOn": today.isoformat(),
            }
        }

        # Check at exactly midnight of tomorrow
        event = api.get_current_event(tomorrow)
        assert event is not None
        assert event.event_type == OutageEventType.DEFINITE
