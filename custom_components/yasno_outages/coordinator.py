"""Coordinator for Yasno outages integration."""

import logging
from pathlib import Path

import recurring_ical_events
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from icalendar import Calendar

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)


class YasnoOutagesCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Yasno outages data."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=None,  # No polling, update manually
        )
        self.hass = hass
        self.group = config_entry.options.get("group", config_entry.data.get("group"))

    async def update_config(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        config_entry: ConfigEntry,
    ) -> None:
        """Update configuration."""
        new_group = config_entry.options.get("group")
        if new_group and new_group != self.group:
            LOGGER.debug("Updating group from %s -> %s", self.group, new_group)
            self.group = new_group
            await self.async_refresh()
        else:
            LOGGER.debug("No group update necessary.")

    async def _async_update_data(self) -> None:
        """Fetch data from ICS file."""
        try:
            LOGGER.debug("Reading ICS file for group %s", self.group)
            return await self.hass.async_add_executor_job(self._read_ical)
        except FileNotFoundError as err:
            LOGGER.exception("ICS file for group %s not found", self.group)
            msg = f"File not found: {err}"
            raise UpdateFailed(msg) from err

    def _read_ical(self) -> recurring_ical_events.UnfoldableCalendar:
        """Read and parse the ICS file."""
        calendar_path = Path(__file__).parent / f"schedules/group-{self.group}.ics"
        with calendar_path.open() as file:
            ical = Calendar.from_ical(file.read())
            return recurring_ical_events.of(ical)
