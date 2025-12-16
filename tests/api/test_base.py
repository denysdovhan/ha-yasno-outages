"""Tests for Base Yasno API."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.yasno_outages.api.base import BaseYasnoApi
from custom_components.yasno_outages.api.models import (
    OutageEvent,
    OutageEventType,
    OutageSlot,
    OutageSource,
)

TEST_REGION_ID = 25
TEST_PROVIDER_ID = 902
TEST_GROUP = "3.1"


# Create a concrete implementation for testing
class ConcreteYasnoApi(BaseYasnoApi):
    """Concrete implementation of BaseYasnoApi for testing."""

    def __init__(
        self,
        region_id: int | None = None,
        provider_id: int | None = None,
        group: str | None = None,
    ) -> None:
        """Initialize the TestableYasnoApi."""
        super().__init__(region_id, provider_id, group)
        self._events = []

    def get_current_event(self, at: datetime.datetime) -> OutageEvent | None:
        """Return outage event that is active at provided time."""
        for event in self._events:
            if event.start <= at < event.end:
                return event
        return None

    def get_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Return outage events that intersect provided range."""
        return [
            event
            for event in self._events
            if (
                start_date <= event.start <= end_date
                or start_date <= event.end <= end_date
                or event.start <= start_date <= event.end
                or event.start <= end_date <= event.end
            )
        ]


@pytest.fixture(name="api")
def _api():
    """Create an API instance."""
    return ConcreteYasnoApi(
        region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP
    )


class TestBaseYasnoApiInit:
    """Test BaseYasnoApi initialization."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        api = ConcreteYasnoApi(
            region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP
        )
        assert api.region_id == TEST_REGION_ID
        assert api.provider_id == TEST_PROVIDER_ID
        assert api.group == TEST_GROUP
        assert api.regions_data is None

    def test_init_without_params(self):
        """Test initialization without parameters."""
        api = ConcreteYasnoApi()
        assert api.region_id is None
        assert api.provider_id is None
        assert api.group is None


class TestBaseYasnoApiFetchData:
    """Test data fetching methods."""

    async def test_fetch_regions_success(self, api, regions_data):
        """Test successful regions fetch."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value=regions_data)
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value.__aenter__.return_value = mock_response

            await api.fetch_regions()
            assert api.regions_data == regions_data

    async def test_fetch_regions_error(self, api):
        """Test regions fetch with error."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.side_effect = aiohttp.ClientError()
            await api.fetch_regions()
            assert api.regions_data is None

    async def test_get_data_success(self, api):
        """Test successful data fetch."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            test_data = {"key": "value"}
            mock_response.json = AsyncMock(return_value=test_data)
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value.__aenter__.return_value = mock_response

            async with aiohttp.ClientSession() as session:
                result = await api._get_data(session, "https://example.com")
                assert result == test_data

    async def test_get_data_error(self, api):
        """Test data fetch with error."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.side_effect = aiohttp.ClientError()

            async with aiohttp.ClientSession() as session:
                result = await api._get_data(session, "https://example.com")
                assert result is None


class TestBaseYasnoApiRegions:
    """Test region-related methods."""

    def test_get_regions(self, api, regions_data):
        """Test getting regions list."""
        api.regions_data = regions_data
        assert api.get_regions() == regions_data

    def test_get_regions_empty(self, api):
        """Test getting regions when none loaded."""
        assert api.get_regions() == []

    def test_get_region_by_name(self, api, regions_data):
        """Test getting region by name."""
        api.regions_data = regions_data
        region = api.get_region_by_name("Київ")
        assert region is not None
        assert region["id"] == TEST_REGION_ID

    def test_get_region_by_name_not_found(self, api, regions_data):
        """Test getting non-existent region."""
        api.regions_data = regions_data
        region = api.get_region_by_name("NonExistent")
        assert region is None

    def test_get_providers_for_region(self, api, regions_data):
        """Test getting providers for region."""
        api.regions_data = regions_data
        providers = api.get_providers_for_region("Київ")
        assert len(providers) == 1
        assert providers[0]["id"] == TEST_PROVIDER_ID

    def test_get_providers_for_nonexistent_region(self, api, regions_data):
        """Test getting providers for non-existent region."""
        api.regions_data = regions_data
        providers = api.get_providers_for_region("NonExistent")
        assert providers == []

    def test_get_provider_by_name(self, api, regions_data):
        """Test getting provider by name."""
        api.regions_data = regions_data
        provider = api.get_provider_by_name(
            "Київ", "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»"
        )
        assert provider is not None
        assert provider["id"] == TEST_PROVIDER_ID

    def test_get_provider_by_name_not_found(self, api, regions_data):
        """Test getting non-existent provider."""
        api.regions_data = regions_data
        provider = api.get_provider_by_name("Київ", "NonExistent")
        assert provider is None


class TestBaseYasnoApiTimeConversion:
    """Test time conversion methods."""

    def test_minutes_to_time(self, today):
        """Test converting minutes to time."""
        result = BaseYasnoApi.minutes_to_time(960, today)
        assert result.hour == 16
        assert result.minute == 0

    def test_minutes_to_time_midnight(self, today):
        """Test converting 0 minutes to midnight."""
        result = BaseYasnoApi.minutes_to_time(0, today)
        assert result.hour == 0
        assert result.minute == 0

    def test_minutes_to_time_end_of_day(self, today, tomorrow):
        """Test converting 24:00 to next day midnight."""
        result = BaseYasnoApi.minutes_to_time(1440, today)
        assert result.hour == 0
        assert result.minute == 0
        assert result.date() == tomorrow.date()


class TestBaseYasnoApiSlotParsing:
    """Test slot parsing methods."""

    def test_parse_raw_slots(self):
        """Test parsing raw slot dictionaries."""
        raw_slots = [
            {"start": 960, "end": 1200, "type": "Definite"},
            {"start": 1200, "end": 1440, "type": "NotPlanned"},
        ]
        slots = BaseYasnoApi._parse_raw_slots(raw_slots)
        assert len(slots) == 2
        assert slots[0].start == 960
        assert slots[0].end == 1200
        assert slots[0].event_type == OutageEventType.DEFINITE

    def test_parse_raw_slots_invalid(self):
        """Test parsing raw slots with invalid data."""
        raw_slots = [
            {"start": 960, "end": 1200, "type": "Definite"},
            {"start": 1200},  # Missing fields
            {"start": 1200, "end": 1440, "type": "InvalidType"},
        ]
        slots = BaseYasnoApi._parse_raw_slots(raw_slots)
        assert len(slots) == 1  # Only valid slot parsed

    def test_parse_slots_to_events(self, today):
        """Test converting slots to events."""
        slots = [
            OutageSlot(start=960, end=1200, event_type=OutageEventType.DEFINITE),
            OutageSlot(start=1200, end=1440, event_type=OutageEventType.NOT_PLANNED),
        ]
        events = BaseYasnoApi._parse_slots_to_events(slots, today, OutageSource.PLANNED)
        assert len(events) == 2
        assert events[0].start.hour == 16
        assert events[0].end.hour == 20
        assert events[0].source == OutageSource.PLANNED


class TestBaseYasnoApiNextEvent:
    """Test get_next_event method."""

    def test_get_next_event(self, api, today):
        """Test getting next event."""
        event1 = OutageEvent(
            start=today.replace(hour=10),
            end=today.replace(hour=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=today.replace(hour=16),
            end=today.replace(hour=18),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        api._events = [event1, event2]

        at = today.replace(hour=8)
        next_event = api.get_next_event(at)
        assert next_event == event1

    def test_get_next_event_after_first(self, api, today):
        """Test getting next event when first has passed."""
        event1 = OutageEvent(
            start=today.replace(hour=10),
            end=today.replace(hour=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=today.replace(hour=16),
            end=today.replace(hour=18),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        api._events = [event1, event2]

        at = today.replace(hour=13)
        next_event = api.get_next_event(at)
        assert next_event == event2

    def test_get_next_event_none(self, api, today):
        """Test getting next event when none exist."""
        event = OutageEvent(
            start=today.replace(hour=10),
            end=today.replace(hour=12),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        api._events = [event]

        at = today.replace(hour=20)
        next_event = api.get_next_event(at)
        assert next_event is None

    def test_get_next_event_filtered_by_type(self, api, today):
        """Test getting next event filtered by type."""
        event1 = OutageEvent(
            start=today.replace(hour=10),
            end=today.replace(hour=12),
            event_type=OutageEventType.NOT_PLANNED,
            source=OutageSource.PLANNED,
        )
        event2 = OutageEvent(
            start=today.replace(hour=16),
            end=today.replace(hour=18),
            event_type=OutageEventType.DEFINITE,
            source=OutageSource.PLANNED,
        )
        api._events = [event1, event2]

        at = today.replace(hour=8)
        next_event = api.get_next_event(at, event_type=OutageEventType.DEFINITE)
        assert next_event == event2
