"""Yasno Outages API package."""

from .models import OutageEvent, OutageEventType, OutageSlot, YasnoApiError
from .planned import PlannedOutagesApi
from .probable import ProbableOutagesApi


class YasnoApi:
    """Facade for Yasno API providing access to planned and probable outages."""

    def __init__(
        self,
        region_id: int | None = None,
        provider_id: int | None = None,
        group: str | None = None,
    ) -> None:
        """Initialize the YasnoApi facade."""
        self._planned = PlannedOutagesApi(region_id, provider_id, group)
        self._probable = ProbableOutagesApi(region_id, provider_id, group)

    @property
    def planned(self) -> PlannedOutagesApi:
        """Get the planned outages API."""
        return self._planned

    @property
    def probable(self) -> ProbableOutagesApi:
        """Get the probable outages API."""
        return self._probable

    @property
    def regions_data(self) -> dict | None:
        """Get shared regions data."""
        return self._planned.regions_data

    @regions_data.setter
    def regions_data(self, value: dict | None) -> None:
        """Set shared regions data for both APIs."""
        self._planned.regions_data = value
        self._probable.regions_data = value

    async def fetch_regions(self) -> None:
        """Fetch regions data (shared between APIs)."""
        await self._planned.fetch_regions()
        # Share the regions data with probable API
        self._probable.regions_data = self._planned.regions_data

    def get_regions(self) -> list[dict]:
        """Get a list of available regions."""
        return self._planned.get_regions()

    def get_region_by_name(self, region_name: str) -> dict | None:
        """Get region data by name."""
        return self._planned.get_region_by_name(region_name)

    def get_providers_for_region(self, region_name: str) -> list[dict]:
        """Get providers (dsos) for a specific region."""
        return self._planned.get_providers_for_region(region_name)

    def get_provider_by_name(
        self,
        region_name: str,
        provider_name: str,
    ) -> dict | None:
        """Get provider data by name."""
        return self._planned.get_provider_by_name(region_name, provider_name)

    async def fetch_streets(
        self,
        region_id: int | None,
        provider_id: int | None,
        query: str,
    ) -> list[dict]:
        """Fetch streets by query."""
        return await self._planned.fetch_streets(region_id, provider_id, query)

    async def fetch_houses(
        self,
        region_id: int | None,
        provider_id: int | None,
        street_id: int | None,
        query: str,
    ) -> list[dict]:
        """Fetch houses by street and query."""
        return await self._planned.fetch_houses(
            region_id,
            provider_id,
            street_id,
            query,
        )

    async def fetch_group_by_address(
        self,
        region_id: int | None,
        provider_id: int | None,
        street_id: int | None,
        house_id: int | None,
    ) -> str | None:
        """Fetch group by address ids."""
        return await self._planned.fetch_group_by_address(
            region_id,
            provider_id,
            street_id,
            house_id,
        )


__all__ = [
    "OutageEvent",
    "OutageEventType",
    "OutageSlot",
    "PlannedOutagesApi",
    "ProbableOutagesApi",
    "YasnoApi",
    "YasnoApiError",
]
