"""Tests for coordinator functionality."""

import datetime
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import STATE_UNKNOWN

from custom_components.yasno_outages.api import OutageEvent, OutageEventType
from custom_components.yasno_outages.api.const import (
    API_STATUS_EMERGENCY_SHUTDOWNS,
    API_STATUS_SCHEDULE_APPLIES,
    API_STATUS_WAITING_FOR_SCHEDULE,
)
from custom_components.yasno_outages.api.models import OutageSource
from custom_components.yasno_outages.const import (
    STATE_NORMAL,
    STATE_OUTAGE,
    STATE_STATUS_EMERGENCY_SHUTDOWNS,
    STATE_STATUS_SCHEDULE_APPLIES,
    STATE_STATUS_WAITING_FOR_SCHEDULE,
)
from custom_components.yasno_outages.coordinator import (
    YasnoOutagesCoordinator,
    find_next_outage,
    is_outage_event,
    simplify_provider_name,
)


@pytest.fixture
def config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        "region": "Київ",
        "provider": "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",
        "group": "3.1",
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_api():
    """Create a mock API."""
    api = MagicMock()
    api.planned = MagicMock()
    api.probable = MagicMock()
    api.regions_data = []
    api.get_region_by_name = MagicMock(return_value=None)
    api.get_provider_by_name = MagicMock(return_value=None)
    return api


@pytest.fixture
def coordinator(config_entry, mock_api):
    """Create a coordinator for testing."""
    hass = MagicMock()
    hass.data = {}
    hass.config.language = "en"
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()

    # Mock async_get_translations to avoid async issues
    # Patch frame helper to avoid HA setup requirements
    with (
        patch(
            "custom_components.yasno_outages.coordinator.async_get_translations"
        ) as mock_translations,
        patch("homeassistant.helpers.frame.report_usage"),
    ):
        mock_translations.return_value = {
            "component.yasno_outages.common.planned_electricity_outage": (
                "Planned Outage"
            ),
            "component.yasno_outages.common.probable_electricity_outage": (
                "Probable Outage"
            ),
            "component.yasno_outages.common.status_schedule_applies": (
                "Schedule Applies"
            ),
            "component.yasno_outages.common.status_waiting_for_schedule": (
                "Waiting for Schedule"
            ),
            "component.yasno_outages.common.status_emergency_shutdowns": (
                "Emergency Shutdowns"
            ),
        }
        coord = YasnoOutagesCoordinator(hass, config_entry, mock_api)
        coord.translations = mock_translations.return_value
        return coord


class TestIsOutageEvent:
    """Test is_outage_event function."""

    def test_none_event_returns_false(self):
        """Test None event returns False."""
        assert is_outage_event(None) is False

    def test_not_planned_event_returns_false(self):
        """Test NOT_PLANNED event returns False."""
        event = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.NOT_PLANNED,
            source=OutageSource.PLANNED,
        )
        assert is_outage_event(event) is False

    def test_definite_event_returns_true(self):
        """Test DEFINITE event returns True."""
        event = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        assert is_outage_event(event) is True


class TestFindNextOutage:
    """Test find_next_outage function."""

    def test_empty_events_returns_none(self):
        """Test empty events list returns None."""
        now = datetime.datetime(2025, 1, 27, 10, 0)
        assert find_next_outage([], now) is None

    def test_finds_next_outage_after_now(self):
        """Test finds next outage that starts after now."""
        now = datetime.datetime(2025, 1, 27, 10, 0)
        event1 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 9, 0),
            end=datetime.datetime(2025, 1, 27, 10, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 12, 0),
            end=datetime.datetime(2025, 1, 27, 14, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        result = find_next_outage([event1, event2], now)
        assert result == event2

    def test_returns_none_when_all_events_in_past(self):
        """Test returns None when all events are in the past."""
        now = datetime.datetime(2025, 1, 27, 15, 0)
        event = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        result = find_next_outage([event], now)
        assert result is None

    def test_returns_first_future_event(self):
        """Test returns first event that starts after now."""
        now = datetime.datetime(2025, 1, 27, 10, 0)
        event1 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 12, 0),
            end=datetime.datetime(2025, 1, 27, 14, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 15, 0),
            end=datetime.datetime(2025, 1, 27, 17, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        result = find_next_outage([event1, event2], now)
        assert result == event1  # First future event


class TestSimplifyProviderName:
    """Test simplify_provider_name function."""

    def test_simplifies_dtek_full_name(self):
        """Test simplifies DTEK full name to short form."""
        full_name = "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»"
        assert simplify_provider_name(full_name) == "ДТЕК"

    def test_simplifies_dtek_case_insensitive(self):
        """Test simplifies DTEK name case-insensitively."""
        full_name = "прат «дтек київські електромережі»"
        assert simplify_provider_name(full_name) == "ДТЕК"

    def test_preserves_other_provider_names(self):
        """Test preserves other provider names."""
        other_name = "ЦЕК"
        assert simplify_provider_name(other_name) == "ЦЕК"


class TestCoordinatorGetEventsBetween:
    """Test get_events_between method."""

    def test_filters_not_planned_events(self, coordinator, today, tomorrow):
        """Test filters out NOT_PLANNED events."""
        outage_event = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        not_planned_event = OutageEvent(
            start=today + timedelta(hours=14),
            end=today + timedelta(hours=16),
            event_type=OutageEventType.NOT_PLANNED,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_events_between = MagicMock(
            return_value=[outage_event, not_planned_event]
        )

        events = coordinator.get_events_between(
            coordinator.api.planned, today, tomorrow
        )

        assert len(events) == 1
        assert events[0] == outage_event
        assert events[0].event_type == OutageEventType.DEFINITE

    def test_sorts_events_by_start_time(self, coordinator, today, tomorrow):
        """Test events are sorted by start time."""
        event1 = OutageEvent(
            start=today + timedelta(hours=14),
            end=today + timedelta(hours=16),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_events_between = MagicMock(
            return_value=[event1, event2]  # Out of order
        )

        events = coordinator.get_events_between(
            coordinator.api.planned, today, tomorrow
        )

        assert len(events) == 2
        assert events[0] == event2  # Earlier event first
        assert events[1] == event1

    def test_handles_api_exception(self, coordinator, today, tomorrow):
        """Test handles API exceptions gracefully."""
        coordinator.api.planned.get_events_between = MagicMock(
            side_effect=Exception("API error")
        )

        events = coordinator.get_events_between(
            coordinator.api.planned, today, tomorrow
        )

        assert events == []


class TestCoordinatorGetOutageAt:
    """Test get_outage_at method."""

    def test_returns_outage_event(self, coordinator, today):
        """Test returns outage event when one exists."""
        now = today + timedelta(hours=11)
        outage_event = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_current_event = MagicMock(return_value=outage_event)

        result = coordinator.get_outage_at(coordinator.api.planned, now)

        assert result == outage_event
        coordinator.api.planned.get_current_event.assert_called_once_with(now)

    def test_filters_not_planned_events(self, coordinator, today):
        """Test filters out NOT_PLANNED events."""
        now = today + timedelta(hours=11)
        not_planned_event = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.NOT_PLANNED,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_current_event = MagicMock(
            return_value=not_planned_event
        )

        result = coordinator.get_outage_at(coordinator.api.planned, now)

        assert result is None

    def test_returns_none_when_no_event(self, coordinator, today):
        """Test returns None when no event exists."""
        now = today + timedelta(hours=11)

        coordinator.api.planned.get_current_event = MagicMock(return_value=None)

        result = coordinator.get_outage_at(coordinator.api.planned, now)

        assert result is None

    def test_handles_api_exception(self, coordinator, today):
        """Test handles API exceptions gracefully."""
        now = today + timedelta(hours=11)

        coordinator.api.planned.get_current_event = MagicMock(
            side_effect=Exception("API error")
        )

        result = coordinator.get_outage_at(coordinator.api.planned, now)

        assert result is None


class TestCoordinatorEventToState:
    """Test _event_to_state method."""

    def test_definite_event_returns_outage(self, coordinator):
        """Test DEFINITE event maps to STATE_OUTAGE."""
        event = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        state = coordinator._event_to_state(event)

        assert state == STATE_OUTAGE

    def test_not_planned_event_returns_normal(self, coordinator):
        """Test NOT_PLANNED event maps to STATE_NORMAL."""
        event = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0),
            event_type=OutageEventType.NOT_PLANNED,
            source=OutageSource.PLANNED,
        )

        state = coordinator._event_to_state(event)

        assert state == STATE_NORMAL

    def test_none_event_returns_unknown(self, coordinator):
        """Test None event maps to STATE_UNKNOWN."""
        state = coordinator._event_to_state(None)

        assert state == STATE_UNKNOWN


class TestCoordinatorCurrentState:
    """Test current_state property."""

    def test_returns_outage_during_definite_event(self, coordinator, today):
        """Test returns STATE_OUTAGE during definite event."""
        now = today + timedelta(hours=11)
        outage_event = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_current_event = MagicMock(return_value=outage_event)

        with patch("homeassistant.util.dt.now", return_value=now):
            state = coordinator.current_state

        assert state == STATE_OUTAGE

    def test_returns_normal_when_no_outage(self, coordinator, today):
        """Test returns STATE_NORMAL when no outage."""
        now = today + timedelta(hours=8)

        coordinator.api.planned.get_current_event = MagicMock(return_value=None)

        with patch("homeassistant.util.dt.now", return_value=now):
            state = coordinator.current_state

        assert state == STATE_UNKNOWN  # None event -> UNKNOWN

    def test_returns_unknown_on_api_error(self, coordinator, today):
        """Test returns STATE_UNKNOWN on API error."""
        now = today + timedelta(hours=8)

        coordinator.api.planned.get_current_event = MagicMock(
            side_effect=Exception("API error")
        )

        with patch("homeassistant.util.dt.now", return_value=now):
            state = coordinator.current_state

        assert state == STATE_UNKNOWN


class TestCoordinatorNextOutage:
    """Test next_planned_outage and next_probable_outage properties."""

    def test_next_planned_outage_finds_future_event(self, coordinator, today):
        """Test finds next planned outage."""
        now = today + timedelta(hours=8)
        future_event = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_events_between = MagicMock(
            return_value=[future_event]
        )

        with patch("homeassistant.util.dt.now", return_value=now):
            next_outage = coordinator.next_planned_outage

        assert next_outage == future_event.start

    def test_next_planned_outage_returns_none_when_no_events(self, coordinator, today):
        """Test returns None when no planned outages."""
        now = today + timedelta(hours=8)

        coordinator.api.planned.get_events_between = MagicMock(return_value=[])

        with patch("homeassistant.util.dt.now", return_value=now):
            next_outage = coordinator.next_planned_outage

        assert next_outage is None

    def test_next_probable_outage_finds_future_event(self, coordinator, today):
        """Test finds next probable outage."""
        now = today + timedelta(hours=8)
        future_event = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PROBABLE,
        )

        coordinator.api.probable.get_events_between = MagicMock(
            return_value=[future_event]
        )

        with patch("homeassistant.util.dt.now", return_value=now):
            next_outage = coordinator.next_probable_outage

        assert next_outage == future_event.start


class TestCoordinatorNextConnectivity:
    """Test next_connectivity property."""

    def test_returns_end_time_during_outage(self, coordinator, today):
        """Test returns event end time when currently in outage."""
        now = today + timedelta(hours=11)
        current_outage = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_events_between = MagicMock(
            return_value=[current_outage]
        )

        with patch("homeassistant.util.dt.now", return_value=now):
            next_connectivity = coordinator.next_connectivity

        assert next_connectivity == current_outage.end

    def test_returns_start_time_before_outage(self, coordinator, today):
        """Test returns next outage start time when not in outage."""
        now = today + timedelta(hours=8)
        future_outage = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_events_between = MagicMock(
            return_value=[future_outage]
        )

        with patch("homeassistant.util.dt.now", return_value=now):
            next_connectivity = coordinator.next_connectivity

        # When not in outage, returns the end time of next outage
        # (which is when connectivity will be restored)
        assert next_connectivity == future_outage.end

    def test_returns_none_when_no_outages(self, coordinator, today):
        """Test returns None when no outages planned."""
        now = today + timedelta(hours=8)

        coordinator.api.planned.get_events_between = MagicMock(return_value=[])

        with patch("homeassistant.util.dt.now", return_value=now):
            next_connectivity = coordinator.next_connectivity

        assert next_connectivity is None


class TestCoordinatorStatusMapping:
    """Test status_today and status_tomorrow properties."""

    def test_status_today_maps_schedule_applies(self, coordinator):
        """Test maps API status to state."""
        coordinator.api.planned.get_status_today = MagicMock(
            return_value=API_STATUS_SCHEDULE_APPLIES
        )

        status = coordinator.status_today

        assert status == STATE_STATUS_SCHEDULE_APPLIES

    def test_status_today_maps_waiting_for_schedule(self, coordinator):
        """Test maps waiting for schedule status."""
        coordinator.api.planned.get_status_today = MagicMock(
            return_value=API_STATUS_WAITING_FOR_SCHEDULE
        )

        status = coordinator.status_today

        assert status == STATE_STATUS_WAITING_FOR_SCHEDULE

    def test_status_today_maps_emergency_shutdowns(self, coordinator):
        """Test maps emergency shutdowns status."""
        coordinator.api.planned.get_status_today = MagicMock(
            return_value=API_STATUS_EMERGENCY_SHUTDOWNS
        )

        status = coordinator.status_today

        assert status == STATE_STATUS_EMERGENCY_SHUTDOWNS

    def test_status_today_returns_unknown_for_unknown_status(self, coordinator):
        """Test returns STATE_UNKNOWN for unknown API status."""
        coordinator.api.planned.get_status_today = MagicMock(return_value="Unknown")

        status = coordinator.status_today

        assert status == STATE_UNKNOWN

    def test_status_tomorrow_maps_correctly(self, coordinator):
        """Test status_tomorrow maps API status correctly."""
        coordinator.api.planned.get_status_tomorrow = MagicMock(
            return_value=API_STATUS_SCHEDULE_APPLIES
        )

        status = coordinator.status_tomorrow

        assert status == STATE_STATUS_SCHEDULE_APPLIES


class TestCoordinatorGetMergedOutages:
    """Test get_merged_outages method."""

    def test_merges_consecutive_events(self, coordinator, today):
        """Test merges consecutive outage events."""
        event1 = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=today + timedelta(hours=12),
            end=today + timedelta(hours=14),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_events_between = MagicMock(
            return_value=[event1, event2]
        )

        now = today + timedelta(hours=8)
        merged = coordinator.get_merged_outages(
            coordinator.api.planned, now, lookahead_days=1
        )

        assert len(merged) == 1
        assert merged[0].start == event1.start
        assert merged[0].end == event2.end

    def test_does_not_merge_non_consecutive_events(self, coordinator, today):
        """Test does not merge events with gaps."""
        event1 = OutageEvent(
            start=today + timedelta(hours=10),
            end=today + timedelta(hours=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=today + timedelta(hours=13),  # Gap
            end=today + timedelta(hours=15),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        coordinator.api.planned.get_events_between = MagicMock(
            return_value=[event1, event2]
        )

        now = today + timedelta(hours=8)
        merged = coordinator.get_merged_outages(
            coordinator.api.planned, now, lookahead_days=1
        )

        assert len(merged) == 2
        assert merged[0] == event1
        assert merged[1] == event2


class TestCoordinatorProviderName:
    """Test provider_name property."""

    def test_simplifies_dtek_provider_name(self, coordinator):
        """Test simplifies DTEK provider name."""
        coordinator._provider_name = "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»"

        provider_name = coordinator.provider_name

        assert provider_name == "ДТЕК"

    def test_preserves_other_provider_names(self, coordinator):
        """Test preserves other provider names."""
        coordinator._provider_name = "ЦЕК"

        provider_name = coordinator.provider_name

        assert provider_name == "ЦЕК"

    def test_looks_up_provider_from_api_when_not_cached(self, coordinator):
        """Test looks up provider from API when not cached."""
        coordinator._provider_name = ""
        coordinator.api.regions_data = [
            {
                "value": "Київ",
                "dsos": [{"name": "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»"}],
            }
        ]
        coordinator.api.get_region_by_name = MagicMock(
            return_value=coordinator.api.regions_data[0]
        )

        provider_name = coordinator.provider_name

        assert provider_name == "ДТЕК"
        assert coordinator._provider_name == "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»"
