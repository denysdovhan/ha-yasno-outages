"""Base class for Yasno outages API."""

import logging
from abc import ABC, abstractmethod

import requests

from .const import API_ENDPOINT

LOGGER = logging.getLogger(__name__)


class YasnoOutagesApi(ABC):
    """Abstract base class to interact with Yasno outages API."""

    def __init__(self, city: str | None = None, group: str | None = None) -> None:
        """Initialize the YasnoBaseApi with city and group."""
        self.group = group
        self.city = city
        self.api_url = API_ENDPOINT
        self.schedule = None

    def fetch_schedule(self) -> None:
        """Fetch outages from the API and store the raw schedule."""
        try:
            response = requests.get(self.api_url, timeout=60)
            response.raise_for_status()
            self.schedule = response.json()
        except requests.RequestException as error:
            LOGGER.exception("Error fetching schedule from Yasno API: %s", error)  # noqa: TRY401
            self.schedule = {}

    @abstractmethod
    def get_cities(self) -> list[str]:
        """Get a list of available cities."""

    @abstractmethod
    def get_group_schedule(self, city: str, group: str) -> list:
        """Get the schedule for a specific group."""

    @abstractmethod
    def get_events(self) -> list[dict]:
        """Get all events."""

    @abstractmethod
    def get_current_event(self) -> dict | None:
        """Get the current event."""
