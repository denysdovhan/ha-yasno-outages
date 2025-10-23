"""Init file for Yasno Outages integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import Platform

from . import repairs
from .const import CONF_CITY, DEFAULT_CITY
from .coordinator import YasnoOutagesCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def validate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Validate an entry."""
    # Fetch the latest schedule to get updated groups
    coordinator: YasnoOutagesCoordinator = entry.runtime_data
    await hass.async_add_executor_job(coordinator.api.fetch_schedule)

    if coordinator.group_name not in coordinator.list_of_groups:
        LOGGER.warning(
            "Group %s for %s is not found in available groups: %s",
            coordinator.group_name,
            coordinator.city,
            coordinator.list_of_groups,
        )
        repairs.group_not_found_issue(hass, entry, coordinator.city, coordinator.group)
        return False

    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    version = config_entry.version

    if version == 1:
        LOGGER.debug("Migrating: city is set to default city (%s).", DEFAULT_CITY)
        data = {**config_entry.data}
        if CONF_CITY not in data:
            data[CONF_CITY] = DEFAULT_CITY
        hass.config_entries.async_update_entry(config_entry, data=data, version=2)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a new entry."""
    LOGGER.info("Setup entry: %s", entry)
    coordinator = YasnoOutagesCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    if not await validate_entry(hass, entry):
        return False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(coordinator.update_config))
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    LOGGER.info("Unload entry: %s", entry)
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
