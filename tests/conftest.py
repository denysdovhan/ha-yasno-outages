"""Pytest configuration and fixtures."""

from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_utils


@pytest.fixture(name="today")
def _today():
    """Create a today datetime fixture."""
    return dt_utils.as_local(dt_utils.now()).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


@pytest.fixture(name="tomorrow")
def _tomorrow(today):
    """Create a tomorrow datetime fixture."""
    return today + timedelta(days=1)


@pytest.fixture
def regions_data():
    """Sample regions data."""
    return [
        {
            "hasCities": False,
            "dsos": [{"id": 902, "name": "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»"}],
            "id": 25,
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
def planned_outage_data(today, tomorrow):
    """Sample planned outage data."""
    return {
        "3.1": {
            "today": {
                "slots": [
                    {"start": 0, "end": 960, "type": "NotPlanned"},
                    {"start": 960, "end": 1200, "type": "Definite"},
                    {"start": 1200, "end": 1440, "type": "NotPlanned"},
                ],
                "date": today.isoformat(),
                "status": "ScheduleApplies",
            },
            "tomorrow": {
                "slots": [
                    {"start": 0, "end": 900, "type": "NotPlanned"},
                    {"start": 900, "end": 1080, "type": "Definite"},
                    {"start": 1080, "end": 1440, "type": "NotPlanned"},
                ],
                "date": tomorrow.isoformat(),
                "status": "ScheduleApplies",
            },
            "updatedOn": today.isoformat(),
        }
    }


@pytest.fixture
def probable_outage_data():
    """Sample probable outage data."""
    return {
        "25": {
            "dsos": {
                "902": {
                    "groups": {
                        "3.1": {
                            "slots": {
                                "0": [  # Monday
                                    {"start": 480, "end": 720, "type": "Definite"},
                                ],
                                "1": [  # Tuesday
                                    {"start": 600, "end": 900, "type": "Definite"},
                                ],
                                "2": [],  # Wednesday
                                "3": [],  # Thursday
                                "4": [],  # Friday
                                "5": [],  # Saturday
                                "6": [],  # Sunday
                            }
                        }
                    }
                }
            }
        }
    }
