"""Tests for Svitlo Yeah models."""

import datetime

import pytest

from custom_components.svitlo_yeah.models import (
    ConnectivityState,
    PlannedOutageEvent,
    PlannedOutageEventType,
    YasnoPlannedOutageDayStatus,
)


class TestYasnoPlannedOutageEventType:
    """Test YasnoPlannedOutageEventType enum."""

    def test_definite(self):
        """Test DEFINITE type."""
        assert PlannedOutageEventType.DEFINITE == "Definite"

    def test_not_planned(self):
        """Test NOT_PLANNED type."""
        assert PlannedOutageEventType.NOT_PLANNED == "NotPlanned"

    def test_emergency(self):
        """Test EMERGENCY type."""
        assert PlannedOutageEventType.EMERGENCY == "Emergency"


class TestYasnoPlannedOutageDayStatus:
    """Test YasnoPlannedOutageDayStatus enum."""

    def test_schedule_applies(self):
        """Test STATUS_SCHEDULE_APPLIES."""
        assert YasnoPlannedOutageDayStatus.STATUS_SCHEDULE_APPLIES == "ScheduleApplies"

    def test_emergency_shutdowns(self):
        """Test STATUS_EMERGENCY_SHUTDOWNS."""
        assert (
            YasnoPlannedOutageDayStatus.STATUS_EMERGENCY_SHUTDOWNS
            == "EmergencyShutdowns"
        )


class TestConnectivityState:
    """Test ConnectivityState enum."""

    def test_emergency(self):
        """Test STATE_EMERGENCY."""
        assert ConnectivityState.STATE_EMERGENCY == "emergency"

    def test_normal(self):
        """Test STATE_NORMAL."""
        assert ConnectivityState.STATE_NORMAL == "normal"

    def test_planned_outage(self):
        """Test STATE_PLANNED_OUTAGE."""
        assert ConnectivityState.STATE_PLANNED_OUTAGE == "planned_outage"


class TestYasnoPlannedOutageEvent:
    """Test YasnoPlannedOutageEvent dataclass."""

    def test_create_with_datetime(self):
        """Test creating event with datetime."""
        start = datetime.datetime(2025, 1, 27, 10, 0, 0)
        end = datetime.datetime(2025, 1, 27, 12, 0, 0)
        event = PlannedOutageEvent(
            event_type=PlannedOutageEventType.DEFINITE,
            start=start,
            end=end,
        )
        assert event.start == start
        assert event.end == end
        assert event.event_type == PlannedOutageEventType.DEFINITE
        assert event.all_day is False

    def test_create_with_date(self):
        """Test creating event with date."""
        start = datetime.date(2025, 1, 27)
        end = datetime.date(2025, 1, 27)
        event = PlannedOutageEvent(
            event_type=PlannedOutageEventType.EMERGENCY,
            start=start,
            end=end,
            all_day=True,
        )
        assert event.start == start
        assert event.end == end
        assert event.all_day is True

    def test_frozen(self):
        """Test that event is frozen."""
        event = PlannedOutageEvent(
            event_type=PlannedOutageEventType.DEFINITE,
            start=datetime.datetime(2025, 1, 27, 10, 0, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0, 0),
        )
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            event.start = datetime.datetime(2025, 1, 28, 10, 0, 0)
