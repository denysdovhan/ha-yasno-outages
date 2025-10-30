"""Init file for Svitlo Yeah integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import Platform

from .const import CONF_PROVIDER_TYPE, PROVIDER_TYPE_DTEK, PROVIDER_TYPE_YASNO
from .coordinator.dtek import DtekCoordinator
from .coordinator.yasno import YasnoCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a new entry."""
    LOGGER.info("Setup entry: %s", entry)

    provider_type = entry.options.get(
        CONF_PROVIDER_TYPE,
        entry.data.get(CONF_PROVIDER_TYPE, PROVIDER_TYPE_YASNO),
    )

    if provider_type == PROVIDER_TYPE_DTEK:
        coordinator = DtekCoordinator(hass, entry)
    else:
        coordinator = YasnoCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    LOGGER.info("Unload entry: %s", entry)
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
