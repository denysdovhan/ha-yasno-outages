"""Tests for helpers module."""

import datetime

from custom_components.yasno_outages.api import OutageEvent, OutageEventType
from custom_components.yasno_outages.api.models import OutageSource
from custom_components.yasno_outages.helpers import merge_consecutive_outages


class TestMergeConsecutiveOutages:
    """Test merge_consecutive_outages function."""

    def test_empty_list(self):
        """Test merging empty list returns empty list."""
        result = merge_consecutive_outages([])
        assert result == []

    def test_single_event(self):
        """Test single event is returned as-is."""
        event = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        result = merge_consecutive_outages([event])
        assert result == [event]

    def test_merge_consecutive_same_type(self):
        """Test merging consecutive events with same type and source."""
        event1 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 12, 0),
            end=datetime.datetime(2025, 1, 27, 14, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        result = merge_consecutive_outages([event1, event2])

        assert len(result) == 1
        assert result[0].start == event1.start
        assert result[0].end == event2.end
        assert result[0].event_type == OutageEventType.DEFINITE
        assert result[0].source == OutageSource.PLANNED

    def test_no_merge_non_consecutive(self):
        """Test non-consecutive events are not merged."""
        event1 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 13, 0),  # Gap
            end=datetime.datetime(2025, 1, 27, 14, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        result = merge_consecutive_outages([event1, event2])

        assert len(result) == 2
        assert result[0] == event1
        assert result[1] == event2

    def test_no_merge_different_type(self):
        """Test consecutive events with different types are not merged."""
        event1 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 12, 0),
            end=datetime.datetime(2025, 1, 27, 14, 0),
            event_type=OutageEventType.NOT_PLANNED,
            source=OutageSource.PLANNED,
        )

        result = merge_consecutive_outages([event1, event2])

        assert len(result) == 2
        assert result[0] == event1
        assert result[1] == event2

    def test_no_merge_different_source(self):
        """Test consecutive events with different sources are not merged."""
        event1 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 12, 0),
            end=datetime.datetime(2025, 1, 27, 14, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PROBABLE,
        )

        result = merge_consecutive_outages([event1, event2])

        assert len(result) == 2
        assert result[0] == event1
        assert result[1] == event2

    def test_merge_multiple_consecutive(self):
        """Test merging multiple consecutive events."""
        event1 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 12, 0),
            end=datetime.datetime(2025, 1, 27, 14, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event3 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 14, 0),
            end=datetime.datetime(2025, 1, 27, 16, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        result = merge_consecutive_outages([event1, event2, event3])

        assert len(result) == 1
        assert result[0].start == event1.start
        assert result[0].end == event3.end

    def test_merge_mixed_consecutive_and_non_consecutive(self):
        """Test merging with mix of consecutive and non-consecutive events."""
        event1 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 12, 0),
            end=datetime.datetime(2025, 1, 27, 14, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event3 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 16, 0),  # Gap
            end=datetime.datetime(2025, 1, 27, 18, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        result = merge_consecutive_outages([event1, event2, event3])

        assert len(result) == 2
        assert result[0].start == event1.start
        assert result[0].end == event2.end
        assert result[1] == event3
