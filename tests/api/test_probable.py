"""Tests for Probable Outages API."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.yasno_outages.api.models import (
    OutageEventType,
    OutageSource,
    YasnoApiError,
)
from custom_components.yasno_outages.api.probable import ProbableOutagesApi

TEST_REGION_ID = 25
TEST_PROVIDER_ID = 902
TEST_GROUP = "3.1"


@pytest.fixture(name="api")
def _api():
    """Create an API instance."""
    return ProbableOutagesApi(
        region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP
    )


class TestProbableOutagesApiInit:
    """Test ProbableOutagesApi initialization."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        api = ProbableOutagesApi(
            region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP
        )
        assert api.region_id == TEST_REGION_ID
        assert api.provider_id == TEST_PROVIDER_ID
        assert api.group == TEST_GROUP
        assert api.probable_outages_data is None

    def test_init_without_params(self):
        """Test initialization without parameters."""
        api = ProbableOutagesApi()
        assert api.region_id is None
        assert api.provider_id is None
        assert api.group is None


class TestProbableOutagesApiFetchData:
    """Test data fetching methods."""

    async def test_fetch_probable_outages_success(self, api, probable_outage_data):
        """Test successful probable outage fetch."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=probable_outage_data)
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value.__aenter__.return_value = mock_response

            await api.fetch_probable_outages_data()
            assert api.probable_outages_data == probable_outage_data

    async def test_fetch_probable_outages_no_config(self):
        """Test probable outage fetch without region/provider."""
        api = ProbableOutagesApi()
        await api.fetch_probable_outages_data()
        assert api.probable_outages_data is None

    async def test_fetch_probable_outages_error(self, api):
        """Test probable outage fetch with error raises YasnoApiError."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.side_effect = aiohttp.ClientError()
            with pytest.raises(YasnoApiError):
                await api.fetch_probable_outages_data()

    async def test_fetch_data(self, api, probable_outage_data):
        """Test fetch_data method."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=probable_outage_data)
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value.__aenter__.return_value = mock_response

            await api.fetch_data()
            assert api.probable_outages_data == probable_outage_data


class TestProbableOutagesApiSlots:
    """Test slot retrieval methods."""

    def test_get_probable_slots_for_weekday(self, api, probable_outage_data):
        """Test getting slots for a specific weekday."""
        api.probable_outages_data = probable_outage_data
        # Monday = 0
        slots = api.get_probable_slots_for_weekday(0)
        assert len(slots) == 1
        assert slots[0].start == 480
        assert slots[0].end == 720
        assert slots[0].event_type == OutageEventType.DEFINITE

    def test_get_probable_slots_for_tuesday(self, api, probable_outage_data):
        """Test getting slots for Tuesday."""
        api.probable_outages_data = probable_outage_data
        # Tuesday = 1
        slots = api.get_probable_slots_for_weekday(1)
        assert len(slots) == 1
        assert slots[0].start == 600
        assert slots[0].end == 900

    def test_get_probable_slots_for_empty_weekday(self, api, probable_outage_data):
        """Test getting slots for weekday with no slots."""
        api.probable_outages_data = probable_outage_data
        # Wednesday = 2 (empty in test data)
        slots = api.get_probable_slots_for_weekday(2)
        assert len(slots) == 0

    def test_get_probable_slots_no_data(self, api):
        """Test getting slots when no data loaded."""
        slots = api.get_probable_slots_for_weekday(0)
        assert slots == []

    def test_get_probable_slots_wrong_region(self, api, probable_outage_data):
        """Test getting slots for non-existent region."""
        api.probable_outages_data = probable_outage_data
        api.region_id = 999
        slots = api.get_probable_slots_for_weekday(0)
        assert slots == []

    def test_get_probable_slots_wrong_provider(self, api, probable_outage_data):
        """Test getting slots for non-existent provider."""
        api.probable_outages_data = probable_outage_data
        api.provider_id = 999
        slots = api.get_probable_slots_for_weekday(0)
        assert slots == []

    def test_get_probable_slots_wrong_group(self, api, probable_outage_data):
        """Test getting slots for non-existent group."""
        api.probable_outages_data = probable_outage_data
        api.group = "99.9"
        slots = api.get_probable_slots_for_weekday(0)
        assert slots == []


class TestProbableOutagesApiCurrentEvent:
    """Test current event retrieval."""

    def test_get_current_event_monday_morning(self, api, probable_outage_data):
        """Test getting current event on Monday morning during outage."""
        api.probable_outages_data = probable_outage_data
        # Create a Monday at 9:00 (540 minutes) - should be in 480-720 slot
        monday = datetime.datetime(2025, 1, 27, 9, 0, 0)  # This is a Monday
        # Adjust to ensure it's Monday
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        event = api.get_current_event(monday)
        assert event is not None
        assert event.event_type == OutageEventType.DEFINITE
        assert event.source == OutageSource.PROBABLE
        assert event.start.hour == 8  # 480 minutes = 8:00
        assert event.end.hour == 12  # 720 minutes = 12:00

    def test_get_current_event_outside_slot(self, api, probable_outage_data):
        """Test getting current event outside any slot."""
        api.probable_outages_data = probable_outage_data
        # Monday at 14:00 - no slot at this time
        monday = datetime.datetime(2025, 1, 27, 14, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        event = api.get_current_event(monday)
        assert event is None

    def test_get_current_event_tuesday(self, api, probable_outage_data):
        """Test getting current event on Tuesday."""
        api.probable_outages_data = probable_outage_data
        # Tuesday at 11:00 (660 minutes) - should be in 600-900 slot
        tuesday = datetime.datetime(2025, 1, 28, 11, 0, 0)
        while tuesday.weekday() != 1:
            tuesday += datetime.timedelta(days=1)

        event = api.get_current_event(tuesday)
        assert event is not None
        assert event.event_type == OutageEventType.DEFINITE
        assert event.start.hour == 10  # 600 minutes = 10:00
        assert event.end.hour == 15  # 900 minutes = 15:00

    def test_get_current_event_no_data(self, api):
        """Test getting current event with no data."""
        monday = datetime.datetime(2025, 1, 27, 9, 0, 0)
        event = api.get_current_event(monday)
        assert event is None

    def test_get_current_event_empty_weekday(self, api, probable_outage_data):
        """Test getting current event on weekday with no slots."""
        api.probable_outages_data = probable_outage_data
        # Wednesday (2) has no slots
        wednesday = datetime.datetime(2025, 1, 29, 10, 0, 0)
        while wednesday.weekday() != 2:
            wednesday += datetime.timedelta(days=1)

        event = api.get_current_event(wednesday)
        assert event is None


class TestProbableOutagesApiEventsBetween:
    """Test events between date range."""

    def test_get_events_between_single_week(self, api, probable_outage_data):
        """Test getting events for a single week."""
        api.probable_outages_data = probable_outage_data
        # Get a full week starting from Monday
        monday = datetime.datetime(2025, 1, 27, 0, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        sunday = monday + datetime.timedelta(days=7)
        events = api.get_events_between(monday, sunday)

        # Should have events for Monday and Tuesday (2 events)
        assert len(events) == 2
        assert all(e.source == OutageSource.PROBABLE for e in events)

    def test_get_events_between_multiple_weeks(self, api, probable_outage_data):
        """Test getting events across multiple weeks."""
        api.probable_outages_data = probable_outage_data
        # Get 3 weeks
        monday = datetime.datetime(2025, 1, 27, 0, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        end_date = monday + datetime.timedelta(days=21)
        events = api.get_events_between(monday, end_date)

        # Should have 2 events per week * 3 weeks = 6 events
        assert len(events) == 6

    def test_get_events_between_single_day(self, api, probable_outage_data):
        """Test getting events for a single day."""
        api.probable_outages_data = probable_outage_data
        # Monday only
        monday = datetime.datetime(2025, 1, 27, 0, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        tuesday = monday + datetime.timedelta(days=1)
        events = api.get_events_between(monday, tuesday)

        # Should have 1 event for Monday
        assert len(events) == 1
        assert events[0].start.weekday() == 0  # Monday

    def test_get_events_between_no_data(self, api):
        """Test getting events with no data."""
        start = datetime.datetime(2025, 1, 27, 0, 0, 0)
        end = start + datetime.timedelta(days=7)
        events = api.get_events_between(start, end)
        assert events == []

    def test_get_events_between_sorted(self, api, probable_outage_data):
        """Test that events are sorted by start time."""
        api.probable_outages_data = probable_outage_data
        monday = datetime.datetime(2025, 1, 27, 0, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        end_date = monday + datetime.timedelta(days=7)
        events = api.get_events_between(monday, end_date)

        # Verify events are sorted
        for i in range(len(events) - 1):
            assert events[i].start <= events[i + 1].start

    def test_get_events_between_partial_week(self, api, probable_outage_data):
        """Test getting events for partial week (Wednesday to Friday)."""
        api.probable_outages_data = probable_outage_data
        # Start from Wednesday
        wednesday = datetime.datetime(2025, 1, 29, 0, 0, 0)
        while wednesday.weekday() != 2:
            wednesday += datetime.timedelta(days=1)

        saturday = wednesday + datetime.timedelta(days=3)
        events = api.get_events_between(wednesday, saturday)

        # No events on Wed, Thu, Fri in test data
        assert len(events) == 0

    def test_get_events_between_includes_monday_tuesday(
        self, api, probable_outage_data
    ):
        """Test that events on Monday and Tuesday are included."""
        api.probable_outages_data = probable_outage_data
        # Start from Monday
        monday = datetime.datetime(2025, 1, 27, 0, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        wednesday = monday + datetime.timedelta(days=2)
        events = api.get_events_between(monday, wednesday)

        # Should have Monday and Tuesday events
        assert len(events) == 2
        weekdays = {e.start.weekday() for e in events}
        assert 0 in weekdays  # Monday
        assert 1 in weekdays  # Tuesday


class TestProbableOutagesApiEdgeCases:
    """Test edge cases and special scenarios."""

    def test_weekday_boundary(self, api, probable_outage_data):
        """Test event at weekday boundary."""
        api.probable_outages_data = probable_outage_data
        # Monday at 23:59
        monday = datetime.datetime(2025, 1, 27, 23, 59, 59)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        event = api.get_current_event(monday)
        # Should not be in any slot (slot ends at 12:00)
        assert event is None

    def test_slot_start_boundary(self, api, probable_outage_data):
        """Test event at exact slot start time."""
        api.probable_outages_data = probable_outage_data
        # Monday at exactly 8:00 (480 minutes)
        monday = datetime.datetime(2025, 1, 27, 8, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        event = api.get_current_event(monday)
        assert event is not None
        assert event.start.hour == 8

    def test_slot_end_boundary(self, api, probable_outage_data):
        """Test event at exact slot end time."""
        api.probable_outages_data = probable_outage_data
        # Monday at exactly 12:00 (720 minutes) - should NOT be in slot (exclusive end)
        monday = datetime.datetime(2025, 1, 27, 12, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        event = api.get_current_event(monday)
        assert event is None  # End is exclusive

    def test_before_slot(self, api, probable_outage_data):
        """Test time before slot starts."""
        api.probable_outages_data = probable_outage_data
        # Monday at 7:00 (420 minutes) - before 480
        monday = datetime.datetime(2025, 1, 27, 7, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        event = api.get_current_event(monday)
        assert event is None

    def test_after_slot(self, api, probable_outage_data):
        """Test time after slot ends."""
        api.probable_outages_data = probable_outage_data
        # Monday at 13:00 (780 minutes) - after 720
        monday = datetime.datetime(2025, 1, 27, 13, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        event = api.get_current_event(monday)
        assert event is None

    def test_midnight_event(self, api):
        """Test event at midnight."""
        # Add slot that starts at midnight
        api.probable_outages_data = {
            str(TEST_REGION_ID): {
                "dsos": {
                    str(TEST_PROVIDER_ID): {
                        "groups": {
                            TEST_GROUP: {
                                "slots": {
                                    "0": [  # Monday
                                        {"start": 0, "end": 120, "type": "Definite"},
                                    ],
                                }
                            }
                        }
                    }
                }
            }
        }

        monday = datetime.datetime(2025, 1, 27, 0, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        event = api.get_current_event(monday)
        assert event is not None
        assert event.start.hour == 0
        assert event.end.hour == 2


class TestProbableOutagesApiRecurrence:
    """Test recurring event generation."""

    def test_weekly_recurrence(self, api, probable_outage_data):
        """Test that events recur weekly."""
        api.probable_outages_data = probable_outage_data
        # Get 2 weeks
        monday1 = datetime.datetime(2025, 1, 27, 0, 0, 0)
        while monday1.weekday() != 0:
            monday1 += datetime.timedelta(days=1)

        monday3 = monday1 + datetime.timedelta(days=14)

        events = api.get_events_between(monday1, monday3)

        # Filter Monday events
        monday_events = [e for e in events if e.start.weekday() == 0]
        assert len(monday_events) == 2

        # Check they're exactly 7 days apart
        assert (monday_events[1].start - monday_events[0].start).days == 7

    def test_event_times_consistent_across_weeks(self, api, probable_outage_data):
        """Test that event times are consistent across weeks."""
        api.probable_outages_data = probable_outage_data
        monday = datetime.datetime(2025, 1, 27, 0, 0, 0)
        while monday.weekday() != 0:
            monday += datetime.timedelta(days=1)

        end_date = monday + datetime.timedelta(days=21)
        events = api.get_events_between(monday, end_date)

        # Get all Monday events
        monday_events = [e for e in events if e.start.weekday() == 0]

        # All should have same time of day
        for event in monday_events:
            assert event.start.hour == 8
            assert event.start.minute == 0
            assert event.end.hour == 12
            assert event.end.minute == 0
