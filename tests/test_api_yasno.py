"""Tests for Svitlo Yeah API."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.util import dt as dt_utils

from custom_components.svitlo_yeah.api import YasnoApi
from custom_components.svitlo_yeah.api.yasno import (
    _minutes_to_time,
    _parse_day_schedule,
)
from custom_components.svitlo_yeah.models import PlannedOutageEventType

TEST_REGION_ID = 25
TEST_PROVIDER_ID = 902
TEST_GROUP = "3.1"


@pytest.fixture(name="api")
def _api():
    """Create an API instance."""
    return YasnoApi(
        region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP
    )


@pytest.fixture
def regions_data():
    """Sample regions data."""
    return [
        {
            "hasCities": False,
            "dsos": [
                {"id": TEST_PROVIDER_ID, "name": "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»"}
            ],
            "id": TEST_REGION_ID,
            "value": "Київ",
        },
        {
            "hasCities": True,
            "dsos": [{"id": 301, "name": "ДнЕМ"}, {"id": 303, "name": "ЦЕК"}],
            "id": 3,
            "value": "Дніпро",
        },
    ]


@pytest.fixture
def planned_outage_data():
    """Sample planned outage data."""
    return {
        TEST_GROUP: {
            "today": {
                "slots": [
                    {"start": 0, "end": 960, "type": "NotPlanned"},
                    {"start": 960, "end": 1200, "type": "Definite"},
                    {"start": 1200, "end": 1440, "type": "NotPlanned"},
                ],
                "date": "2025-10-27T00:00:00+02:00",
                "status": "ScheduleApplies",
            },
            "tomorrow": {
                "slots": [
                    {"start": 0, "end": 900, "type": "NotPlanned"},
                    {"start": 900, "end": 1080, "type": "Definite"},
                    {"start": 1080, "end": 1440, "type": "NotPlanned"},
                ],
                "date": "2025-10-28T00:00:00+02:00",
                "status": "ScheduleApplies",
            },
            "updatedOn": "2025-10-27T13:42:41+00:00",
        }
    }


@pytest.fixture
def emergency_outage_data():
    """Sample emergency outage data."""
    return {
        TEST_GROUP: {
            "today": {
                "slots": [],
                "date": "2025-10-27T00:00:00+02:00",
                "status": "EmergencyShutdowns",
            },
            "tomorrow": {
                "slots": [],
                "date": "2025-10-28T00:00:00+02:00",
                "status": "EmergencyShutdowns",
            },
            "updatedOn": "2025-10-27T07:04:31+00:00",
        }
    }


class TestYasnoApiInit:
    """Test YasnoApi initialization."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        api = YasnoApi(
            region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP
        )
        assert api.region_id == TEST_REGION_ID
        assert api.provider_id == TEST_PROVIDER_ID
        assert api.group == TEST_GROUP
        assert api.regions_data is None
        assert api.planned_outage_data is None

    def test_init_without_params(self):
        """Test initialization without parameters."""
        api = YasnoApi()
        assert api.region_id is None
        assert api.provider_id is None
        assert api.group is None


class TestYasnoApiFetchData:
    """Test data fetching methods."""

    async def test_fetch_regions_success(self, api, regions_data):
        """Test successful regions fetch."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=regions_data)
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value.__aenter__.return_value = mock_response

            await api.fetch_yasno_regions()
            assert api.regions_data == regions_data

    async def test_fetch_regions_error(self, api):
        """Test regions fetch with error."""
        YasnoApi._cached_regions_data = None
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.side_effect = aiohttp.ClientError()
            await api.fetch_yasno_regions()
            assert api.regions_data is None

    async def test_fetch_planned_outage_success(self, api, planned_outage_data):
        """Test successful planned outage fetch."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=planned_outage_data)
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value.__aenter__.return_value = mock_response

            await api.fetch_planned_outage_data()
            assert api.planned_outage_data == planned_outage_data

    async def test_fetch_planned_outage_no_config(self, api):
        """Test planned outage fetch without region/provider."""
        api.region_id = None
        await api.fetch_planned_outage_data()
        assert api.planned_outage_data is None


class TestYasnoApiRegions:
    """Test region-related methods."""

    def test_get_regions(self, api, regions_data):
        """Test getting regions list."""
        api.regions_data = regions_data
        assert api.get_yasno_regions() == regions_data

    def test_get_regions_empty(self, api):
        """Test getting regions when none loaded."""
        assert api.get_yasno_regions() == []

    def test_get_region_by_name(self, api, regions_data):
        """Test getting region by name."""
        api.regions_data = regions_data
        region = api.get_region_by_name("Київ")
        assert region["value"] == "Київ"

    def test_get_region_by_name_not_found(self, api, regions_data):
        """Test getting non-existent region."""
        api.regions_data = regions_data
        assert api.get_region_by_name("Unknown") is None

    def test_get_providers_for_region(self, api, regions_data):
        """Test getting providers for region."""
        api.regions_data = regions_data
        providers = api.get_yasno_providers_for_region("Київ")
        assert len(providers) == 1
        assert providers[0]["name"] == "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»"

    def test_get_providers_for_region_not_found(self, api, regions_data):
        """Test getting providers for non-existent region."""
        api.regions_data = regions_data
        assert api.get_yasno_providers_for_region("Unknown") == []

    def test_get_provider_by_name(self, api, regions_data):
        """Test getting provider by name."""
        api.regions_data = regions_data
        provider = api.get_yasno_provider_by_name(
            "Київ", "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»"
        )
        assert provider["id"] == TEST_PROVIDER_ID

    def test_get_provider_by_name_not_found(self, api, regions_data):
        """Test getting non-existent provider."""
        api.regions_data = regions_data
        assert api.get_yasno_provider_by_name("Київ", "Unknown") is None


class TestYasnoApiGroups:
    """Test group-related methods."""

    def test_get_groups(self, api, planned_outage_data):
        """Test getting groups list."""
        api.planned_outage_data = planned_outage_data
        assert api.get_yasno_groups() == [TEST_GROUP]

    def test_get_groups_empty(self, api):
        """Test getting groups when none loaded."""
        assert api.get_yasno_groups() == []


class TestYasnoApiTimeConversion:
    """Test time conversion methods."""

    def test_minutes_to_time(self):
        """Test converting minutes to time."""
        date = dt_utils.now()
        result = _minutes_to_time(960, date)
        assert result.hour == 16
        assert result.minute == 0

    def test_minutes_to_time_end_of_day(self):
        """Test converting 24:00 to time."""
        date = dt_utils.now()
        result = _minutes_to_time(1440, date)
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59


class TestYasnoApiScheduleParsing:
    """Test schedule parsing methods."""

    def test_parse_day_schedule(self):
        """Test parsing day schedule."""
        day_data = {
            "slots": [
                {"start": 960, "end": 1200, "type": "Definite"},
                {"start": 1200, "end": 1440, "type": "NotPlanned"},
            ],
            "date": "2025-01-27T00:00:00+02:00",
        }
        date = dt_utils.parse_datetime("2025-01-27T00:00:00+02:00")
        events = _parse_day_schedule(day_data, date)
        assert len(events) == 1
        assert events[0].event_type == PlannedOutageEventType.DEFINITE
        assert events[0].start.hour == 16

    def test_parse_emergency_shutdown(self, api):
        """Test parsing emergency shutdown."""
        day_data = {
            "status": "EmergencyShutdowns",
            "slots": [],
            "date": "2025-01-27T00:00:00+02:00",
        }
        date = dt_utils.parse_datetime("2025-01-27T00:00:00+02:00")
        api.planned_outage_data = {TEST_GROUP: {"today": day_data}}
        events = api.get_events(date, date + datetime.timedelta(days=1))
        assert len(events) == 1
        assert events[0].all_day is True
        assert events[0].event_type == PlannedOutageEventType.EMERGENCY
        assert events[0].start == datetime.date(2025, 1, 27)


class TestYasnoApiEvents:
    """Test event retrieval methods."""

    def test_get_updated_on(self, api, planned_outage_data):
        """Test getting updated timestamp."""
        api.planned_outage_data = planned_outage_data
        updated = api.get_updated_on()
        assert updated is not None
        assert updated.year == 2025

    def test_get_updated_on_no_data(self, api):
        """Test getting updated timestamp without data."""
        assert api.get_updated_on() is None

    def test_get_events(self, api, planned_outage_data):
        """Test getting events."""
        api.planned_outage_data = planned_outage_data
        start = dt_utils.parse_datetime("2025-10-27T00:00:00+02:00")
        end = dt_utils.parse_datetime("2025-10-28T23:59:59+02:00")
        events = api.get_events(start, end)
        assert len(events) == 2

    def test_get_events_emergency(self, api, emergency_outage_data):
        """Test getting emergency events."""
        api.planned_outage_data = emergency_outage_data
        start = dt_utils.parse_datetime("2025-10-27T00:00:00+02:00")
        end = dt_utils.parse_datetime("2025-10-28T23:59:59+02:00")
        events = api.get_events(start, end)
        assert len(events) == 2
        assert all(e.event_type == PlannedOutageEventType.EMERGENCY for e in events)

    def test_get_current_event(self, api, planned_outage_data):
        """Test getting current event."""
        api.planned_outage_data = planned_outage_data
        at = dt_utils.parse_datetime("2025-10-27T17:00:00+02:00")
        event = api.get_current_event(at)
        assert event is not None
        assert event.event_type == PlannedOutageEventType.DEFINITE

    def test_get_current_event_none(self, api, planned_outage_data):
        """Test getting current event when none active."""
        api.planned_outage_data = planned_outage_data
        at = dt_utils.parse_datetime("2025-10-27T08:00:00+02:00")
        event = api.get_current_event(at)
        assert event is None
