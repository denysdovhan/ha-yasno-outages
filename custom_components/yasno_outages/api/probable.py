"""Probable outages API for Yasno."""

import logging

import aiohttp

from .base import BaseYasnoApi
from .const import PROBABLE_OUTAGES_ENDPOINT
from .models import OutageEventType, ProbableOutageSlot

LOGGER = logging.getLogger(__name__)


class ProbableOutagesApi(BaseYasnoApi):
    """API for fetching probable outages data."""

    def __init__(
        self,
        region_id: int | None = None,
        provider_id: int | None = None,
        group: str | None = None,
    ) -> None:
        """Initialize the ProbableOutagesApi."""
        super().__init__(region_id, provider_id, group)
        self.probable_outages_data = None

    async def fetch_probable_outages_data(self) -> None:
        """Fetch probable outages data for the configured region and provider."""
        if not self.region_id or not self.provider_id:
            LOGGER.warning(
                "Region and Provider ID must be set before fetching probable outages",
            )
            return

        url = PROBABLE_OUTAGES_ENDPOINT.format(
            region_id=self.region_id,
            dso_id=self.provider_id,
        )

        async with aiohttp.ClientSession() as session:
            self.probable_outages_data = await self._get_route_data(session, url)

    def get_probable_slots_for_weekday(
        self,
        weekday: int,
    ) -> list[ProbableOutageSlot]:
        """
        Get probable outage slots for a specific weekday.

        Args:
          weekday: Day of week (0=Monday, 6=Sunday) matching API spec.

        Returns:
          List of ProbableOutageSlot objects for the given weekday.

        """
        if not self.probable_outages_data:
            return []

        # Navigate to the group's slots for the specified weekday
        try:
            region_data = self.probable_outages_data.get(str(self.region_id), {})
            dsos_data = region_data.get("dsos", {})
            dso_data = dsos_data.get(str(self.provider_id), {})
            groups_data = dso_data.get("groups", {})
            group_data = groups_data.get(self.group, {})
            slots_data = group_data.get("slots", {})
            weekday_slots = slots_data.get(str(weekday), [])
        except (AttributeError, KeyError):
            LOGGER.warning(
                "Failed to navigate probable outages data structure for weekday %s",
                weekday,
            )
            return []

        # Parse slots into ProbableOutageSlot objects
        probable_slots = []
        for slot in weekday_slots:
            try:
                event_type = OutageEventType(slot["type"])
                probable_slots.append(
                    ProbableOutageSlot(
                        start=slot["start"],
                        end=slot["end"],
                        event_type=event_type,
                    ),
                )
            except (KeyError, ValueError) as err:
                LOGGER.warning("Failed to parse probable slot: %s", err)
                continue

        return probable_slots

    async def fetch_data(self) -> None:
        """Fetch all required data."""
        await self.fetch_probable_outages_data()
