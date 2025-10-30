"""Tests for DTEK API."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.util import dt as dt_utils

from custom_components.svitlo_yeah.api.dtek import (
    DtekAPI,
    _parse_group_hours,
)

TEST_GROUP = "1.1"
TEST_TIMESTAMP = "1761688800"


@pytest.fixture(name="api")
def _api():
    """Create a DTEK API instance."""
    return DtekAPI(group=TEST_GROUP)


@pytest.fixture
def sample_data():
    """Sample parsed schedule data."""
    return {
        "data": {
            TEST_TIMESTAMP: {
                "GPV1.1": {
                    "1": "yes",
                    "10": "yes",
                    "11": "yes",
                    "12": "yes",
                    "13": "second",
                    "14": "no",
                    "15": "no",
                    "16": "no",
                    "17": "first",
                    "18": "yes",
                    "19": "yes",
                    "2": "yes",
                    "20": "yes",
                    "21": "yes",
                    "22": "yes",
                    "23": "yes",
                    "24": "yes",
                    "3": "yes",
                    "4": "yes",
                    "5": "yes",
                    "6": "yes",
                    "7": "yes",
                    "8": "yes",
                    "9": "yes",
                },
            },
        },
        "update": "29.10.2025 13:51",
        "today": 1761688800,
    }


@pytest.fixture
def sample_html():
    """Sample HTML with DisconSchedule.fact."""
    return """
<html>
<body>
<script>
DisconSchedule.currentWeekDayIndex = 3
DisconSchedule.fact = {"data":{"1761688800":{"GPV1.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"second","14":"no","15":"no","16":"no","17":"first","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV1.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"second","14":"no","15":"no","16":"no","17":"first","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV2.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV2.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"no","16":"no","17":"first","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV3.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"no","18":"no","19":"no","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV3.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"no","10":"first","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV4.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"no","10":"first","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"no","18":"no","19":"no","20":"no","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV4.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"no","10":"no","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"no","18":"no","19":"no","20":"no","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV5.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"no","11":"no","12":"no","13":"no","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV5.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"no","11":"no","12":"no","13":"no","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV6.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"second","21":"no","22":"no","23":"yes","24":"yes"},"GPV6.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"second","21":"no","22":"no","23":"yes","24":"yes"}},"1761775200":{"GPV1.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV1.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV2.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV2.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV3.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV3.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV4.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV4.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV5.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV5.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV6.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV6.2":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"yes","14":"yes","15":"yes","16":"yes","17":"yes","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"}}},"update":"29.10.2025 13:51","today":1761688800}</script><script type="text/javascript" src="/_Incapsula_Resource?SWJIYLWA=719d34d31c8e3a6e6fffd425f7e032f3&ns=1&cb=330913616" async></script></body>
</html>
    """


class TestDtekRegionAPIInit:
    """Test DtekRegionAPI initialization."""

    def test_init_with_group(self):
        """Test initialization with group."""
        api = DtekAPI(group=TEST_GROUP)
        assert api.group == TEST_GROUP
        assert api.data is None

    def test_init_without_group(self):
        """Test initialization without group."""
        api = DtekAPI()
        assert api.group is None

    @pytest.mark.skip(reason="Manual test only - requires real network access")
    async def test_real_data(self):
        """Test fetching real data from DTEK website."""
        api = DtekAPI(group=TEST_GROUP)
        await api.fetch_data(cache_minutes=0)
        assert api.data is not None
        assert "data" in api.data
        assert "update" in api.data


class TestDtekRegionAPIFetchData:
    """Test data fetching methods."""

    async def test_fetch_data_success(self, api, sample_html):
        """Test successful data fetch."""
        with patch(
            "custom_components.svitlo_yeah.api.dtek.aiohttp.ClientSession"
        ) as mock_session_class:
            mock_response = AsyncMock()
            mock_response.text = AsyncMock(return_value=sample_html)
            mock_response.raise_for_status = MagicMock()

            mock_session = AsyncMock()
            mock_session.get = AsyncMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            await api.fetch_data()
            assert api.data is not None
            assert "data" in api.data
            assert TEST_TIMESTAMP in api.data["data"]


class TestDtekRegionAPIGetGroups:
    """Test get_groups method."""

    def test_get_groups_success(self, api, sample_data):
        """Test getting groups list."""
        api.data = sample_data
        groups = api.get_dtek_region_groups()
        assert TEST_GROUP in groups
        assert "1.1" in groups

    def test_get_groups_no_data(self, api):
        """Test getting groups without data."""
        assert api.get_dtek_region_groups() == []

    def test_get_groups_missing_data_key(self, api):
        """Test getting groups with missing data key."""
        api.data = {"update": "29.10.2025 13:51"}
        assert api.get_dtek_region_groups() == []


class TestDtekRegionAPIParseGroupHours:
    """Test _parse_group_hours method."""

    @pytest.mark.parametrize(
        "group_hours,expected",  # noqa: PT006
        [
            # 0 All yes - no outages
            ({str(i): "yes" for i in range(1, 25)}, []),
            # 1 All no - full day outage
            (
                {str(i): "no" for i in range(1, 25)},
                [(datetime.time(0, 0), datetime.time(23, 59, 59))],
            ),
            # 2 One range of no
            (
                {
                    **{str(i): "yes" for i in range(1, 25)},
                    "14": "no",
                    "15": "no",
                    "16": "no",
                },
                [(datetime.time(13, 0), datetime.time(16, 0))],
            ),
            # 3 Two ranges of no
            (
                {
                    **{str(i): "yes" for i in range(1, 25)},
                    "9": "no",
                    "10": "no",
                    "20": "no",
                    "21": "no",
                },
                [
                    (datetime.time(8, 0), datetime.time(10, 0)),
                    (datetime.time(19, 0), datetime.time(21, 0)),
                ],
            ),
            # 4 One range: second + no + first
            (
                {
                    **{str(i): "yes" for i in range(1, 25)},
                    "13": "second",
                    "14": "no",
                    "15": "no",
                    "16": "no",
                    "17": "first",
                },
                [(datetime.time(12, 30), datetime.time(16, 30))],
            ),
            # 5 Two ranges: second + no + first
            (
                {
                    **{str(i): "yes" for i in range(1, 25)},
                    "9": "second",
                    "10": "no",
                    "11": "first",
                    "20": "second",
                    "21": "no",
                    "22": "first",
                },
                [
                    (datetime.time(8, 30), datetime.time(10, 30)),
                    (datetime.time(19, 30), datetime.time(21, 30)),
                ],
            ),
            # 6 Adjacent second + first
            (
                {
                    **{str(i): "yes" for i in range(1, 25)},
                    "21": "second",
                    "22": "first",
                },
                [(datetime.time(20, 30), datetime.time(21, 30))],
            ),
        ],
    )
    def test_parse_group_hours(self, group_hours, expected):
        """Test parsing various group hour patterns."""
        result = _parse_group_hours(group_hours)
        assert result == expected


class TestDtekRegionAPIGetUpdatedOn:
    """Test get_updated_on method."""

    def test_get_updated_on_success(self, api):
        """Test getting updated timestamp."""
        api.data = {
            "data": {},
            "update": "29.10.2025 13:51",
            "today": int(TEST_TIMESTAMP),
        }
        updated = api.get_updated_on()
        assert updated is not None

    def test_get_updated_on_no_data(self, api):
        """Test getting updated timestamp without data."""
        assert api.get_updated_on() is None

    def test_get_updated_on_missing_update(self, api):
        """Test getting updated timestamp with missing update field."""
        api.data = {"data": {}}
        assert api.get_updated_on() is None


class TestDtekRegionAPIGetCurrentEvent:
    """Test get_current_event method."""

    def test_get_current_event_during_outage(self, api, sample_data):
        """Test getting current event during an outage."""
        api.data = sample_data

        # Create a time during the outage (13:00 on the test day)
        day_dt = dt_utils.utc_from_timestamp(int(TEST_TIMESTAMP))
        day_dt = dt_utils.as_local(day_dt)
        current_time = day_dt.replace(hour=13, minute=0)

        event = api.get_current_event(current_time)
        assert event is not None
        assert event.start <= current_time < event.end

    def test_get_current_event_no_outage(self, api, sample_data):
        """Test getting current event when there's no outage."""
        api.data = sample_data

        # Create a time outside the outage (10:00 on the test day)
        day_dt = dt_utils.utc_from_timestamp(int(TEST_TIMESTAMP))
        day_dt = dt_utils.as_local(day_dt)
        current_time = day_dt.replace(hour=10, minute=0)

        event = api.get_current_event(current_time)
        assert event is None

    def test_get_current_event_no_data(self, api):
        """Test getting current event without data."""
        current_time = dt_utils.now()
        assert api.get_current_event(current_time) is None
