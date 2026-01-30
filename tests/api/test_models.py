"""Tests for Yasno Outages models."""

import datetime

import pytest

from custom_components.yasno_outages.api.models import (
    OutageEvent,
    OutageEventType,
    OutageSlot,
    OutageSource,
)


class TestOutageEventType:
    """Test OutageEventType enum."""

    def test_definite(self):
        """Test DEFINITE type."""
        assert OutageEventType.DEFINITE == "Definite"

    def test_not_planned(self):
        """Test NOT_PLANNED type."""
        assert OutageEventType.NOT_PLANNED == "NotPlanned"


class TestOutageSource:
    """Test OutageSource enum."""

    def test_planned(self):
        """Test PLANNED source."""
        assert OutageSource.PLANNED == "planned"

    def test_probable(self):
        """Test PROBABLE source."""
        assert OutageSource.PROBABLE == "probable"


class TestOutageEvent:
    """Test OutageEvent dataclass."""

    def test_create_event(self):
        """Test creating an outage event."""
        start = datetime.datetime(2025, 1, 27, 10, 0, 0)
        end = datetime.datetime(2025, 1, 27, 12, 0, 0)
        event = OutageEvent(
            event_type=OutageEventType.DEFINITE,
            start=start,
            end=end,
            source=OutageSource.PLANNED,
        )
        assert event.start == start
        assert event.end == end
        assert event.event_type == OutageEventType.DEFINITE
        assert event.source == OutageSource.PLANNED

    def test_frozen(self):
        """Test that event is frozen."""
        event = OutageEvent(
            event_type=OutageEventType.DEFINITE,
            start=datetime.datetime(2025, 1, 27, 10, 0, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0, 0),
            source=OutageSource.PLANNED,
        )
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            event.start = datetime.datetime(2025, 1, 28, 10, 0, 0)

    def test_event_with_probable_source(self):
        """Test creating event with probable source."""
        start = datetime.datetime(2025, 1, 27, 10, 0, 0)
        end = datetime.datetime(2025, 1, 27, 12, 0, 0)
        event = OutageEvent(
            event_type=OutageEventType.DEFINITE,
            start=start,
            end=end,
            source=OutageSource.PROBABLE,
        )
        assert event.source == OutageSource.PROBABLE


class TestOutageSlot:
    """Test OutageSlot dataclass."""

    def test_create_slot(self):
        """Test creating an outage slot."""
        slot = OutageSlot(
            start=960,
            end=1200,
            event_type=OutageEventType.DEFINITE,
        )
        assert slot.start == 960
        assert slot.end == 1200
        assert slot.event_type == OutageEventType.DEFINITE

    def test_frozen(self):
        """Test that slot is frozen."""
        slot = OutageSlot(
            start=960,
            end=1200,
            event_type=OutageEventType.DEFINITE,
        )
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            slot.start = 1000

    def test_slot_with_not_planned_type(self):
        """Test creating slot with NotPlanned type."""
        slot = OutageSlot(
            start=0,
            end=960,
            event_type=OutageEventType.NOT_PLANNED,
        )
        assert slot.event_type == OutageEventType.NOT_PLANNED
