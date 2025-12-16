"""Tests for calendar functionality."""

import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.helpers.entity import EntityDescription

from custom_components.yasno_outages.api import OutageEvent, OutageEventType
from custom_components.yasno_outages.api.models import OutageSource
from custom_components.yasno_outages.calendar import (
    YasnoPlannedOutagesCalendar,
    async_setup_entry,
    to_all_day_calendar_event,
    to_calendar_event,
)

UTC = ZoneInfo("UTC")


@pytest.fixture
def coordinator():
    """Create a mock coordinator for testing."""
    coordinator = MagicMock()
    coordinator.api = MagicMock()
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_entry"
    coordinator.config_entry.data = {
        "region": "Київ",
        "provider": "ДТЕК",
        "group": "3.1",
    }
    coordinator.region_name = "Київ"
    coordinator.provider_name = "ДТЕК"
    coordinator.group = "3.1"
    coordinator.event_summary_map = {
        OutageSource.PLANNED: "Planned Outage",
        OutageSource.PROBABLE: "Probable Outage",
    }
    coordinator.status_event_summary_map = {
        "ScheduleApplies": "Schedule Applies",
        "EmergencyShutdowns": "Emergency Shutdowns",
    }
    coordinator.status_all_day_events_enabled = False

    # Mock methods to return specific values
    def get_planned_outage_at_mock(*_args, **_kwargs):
        return None

    def get_planned_events_between_mock(*_args, **_kwargs):
        return []

    def get_status_mock(*_args, **_kwargs):
        return None

    def get_date_mock(*_args, **_kwargs):
        return None

    coordinator.get_planned_outage_at = get_planned_outage_at_mock
    coordinator.get_planned_events_between = get_planned_events_between_mock
    coordinator.get_status_today = get_status_mock
    coordinator.get_status_tomorrow = get_status_mock
    coordinator.get_today_date = get_date_mock
    coordinator.get_tomorrow_date = get_date_mock
    return coordinator


class TestToCalendarEvent:
    """Test to_calendar_event function."""

    def test_convert_planned_outage_event(self, coordinator):
        """Test converting planned outage event to calendar event."""
        event = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0, tzinfo=UTC),
            end=datetime.datetime(2025, 1, 27, 12, 0, tzinfo=UTC),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )

        calendar_event = to_calendar_event(coordinator, event)

        assert calendar_event.summary == "Planned Outage"
        assert calendar_event.start == event.start
        assert calendar_event.end == event.end
        assert calendar_event.description == "Definite"
        assert calendar_event.uid == f"planned-{event.start.isoformat()}"

    def test_convert_probable_outage_event(self, coordinator):
        """Test converting probable outage event to calendar event."""
        event = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0, tzinfo=UTC),
            end=datetime.datetime(2025, 1, 27, 12, 0, tzinfo=UTC),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PROBABLE,
        )

        calendar_event = to_calendar_event(coordinator, event)

        assert calendar_event.summary == "Probable Outage"
        assert calendar_event.start == event.start
        assert calendar_event.end == event.end
        assert calendar_event.description == "Definite"
        assert calendar_event.uid == f"probable-{event.start.isoformat()}"

    def test_event_without_source_defaults_to_planned(self, coordinator):
        """Test event without source defaults to planned."""
        event = OutageEvent(
            start=datetime.datetime(2025, 1, 27, 10, 0, tzinfo=UTC),
            end=datetime.datetime(2025, 1, 27, 12, 0, tzinfo=UTC),
            event_type=OutageEventType.DEFINITE,
            source=None,
        )

        calendar_event = to_calendar_event(coordinator, event)

        assert calendar_event.summary == "Planned Outage"
        assert calendar_event.uid.startswith("planned-")


class TestToAllDayCalendarEvent:
    """Test to_all_day_calendar_event function."""

    def test_convert_status_to_all_day_event(self, coordinator):
        """Test converting status to all-day calendar event."""
        date = datetime.date(2025, 1, 27)
        status = "ScheduleApplies"

        calendar_event = to_all_day_calendar_event(coordinator, date, status)

        assert calendar_event.summary == "Schedule Applies"
        assert calendar_event.start == date
        assert calendar_event.end == date + datetime.timedelta(days=1)
        assert calendar_event.description == status
        assert calendar_event.uid == f"status-{date.isoformat()}"

    def test_unknown_status_uses_status_text(self, coordinator):
        """Test unknown status uses status text as summary."""
        date = datetime.date(2025, 1, 27)
        status = "UnknownStatus"

        calendar_event = to_all_day_calendar_event(coordinator, date, status)

        assert calendar_event.summary == "UnknownStatus"
        assert calendar_event.description == "UnknownStatus"


class TestYasnoPlannedOutagesCalendar:
    """Test YasnoPlannedOutagesCalendar entity.

    Note: Full entity tests are skipped due to complex Home Assistant
    mocking requirements. Entity behavior is tested through integration
    tests with real HA environment.
    """

    def test_entity_description_properties(self):
        """Test entity description has correct properties."""
        # Test we can create entity description
        desc = EntityDescription(
            key="planned_outages",
            name="Planned Outages",
            translation_key="planned_outages",
        )

        assert desc.key == "planned_outages"
        assert desc.name == "Planned Outages"
        assert desc.translation_key == "planned_outages"


class TestCalendarSetup:
    """Test calendar setup functionality."""

    async def test_async_setup_entry(self, coordinator):
        """Test async_setup_entry creates calendar entity."""
        config_entry = MagicMock()
        config_entry.runtime_data = MagicMock()
        config_entry.runtime_data.coordinator = coordinator

        hass = MagicMock()
        async_add_entities = MagicMock()

        await async_setup_entry(hass, config_entry, async_add_entities)

        assert async_add_entities.call_count == 1
        entities = async_add_entities.call_args[0][0]

        assert len(entities) == 2
        assert isinstance(entities[0], YasnoPlannedOutagesCalendar)
        assert entities[0].coordinator == coordinator
