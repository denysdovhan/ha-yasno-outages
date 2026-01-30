"""Init file for Yasno Outages integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.loader import async_get_loaded_integration

from .api import YasnoApi
from .const import (
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_PROVIDER,
    CONF_REGION,
    CONF_SERVICE,
    CONF_STREET_ID,
)
from .coordinator import YasnoOutagesCoordinator
from .data import YasnoOutagesData
from .repairs import async_check_and_create_repair

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .data import YasnoOutagesConfigEntry

LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry to new version."""
    LOGGER.info(
        "Migrating entry %s from version %s",
        entry.entry_id,
        entry.version,
    )

    # Migration from version 1 to 2: rename service -> provider
    if entry.version == 1:
        updated_data = dict(entry.data)
        updated_options = dict(entry.options)

        # Migrate service to provider in data
        if CONF_SERVICE in updated_data:
            LOGGER.info("Migrating service to provider in data")
            updated_data[CONF_PROVIDER] = updated_data.pop(CONF_SERVICE)

        # Migrate service to provider in options
        if CONF_SERVICE in updated_options:
            LOGGER.info("Migrating service to provider in options")
            updated_options[CONF_PROVIDER] = updated_options.pop(CONF_SERVICE)

        # Update entry with new data and version
        hass.config_entries.async_update_entry(
            entry,
            data=updated_data,
            options=updated_options,
            version=2,
        )

        LOGGER.info("Migration to version 2 complete")

    LOGGER.info("Entry %s now at version %s", entry.entry_id, entry.version)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YasnoOutagesConfigEntry,
) -> bool:
    """Set up a new entry."""
    LOGGER.info("Setup entry: %s", entry)

    # Validate required keys are present
    region = entry.options.get(CONF_REGION, entry.data.get(CONF_REGION))
    provider = entry.options.get(CONF_PROVIDER, entry.data.get(CONF_PROVIDER))

    # Check for other issues (like old API format)
    await async_check_and_create_repair(hass, entry)

    if not region or not provider:
        LOGGER.error(
            "Missing required keys for entry %s: region=%s, provider=%s",
            entry.entry_id,
            region,
            provider,
        )
        return False

    # Setup API for resolving region and provider ids
    bootstrap_api = YasnoApi()
    await bootstrap_api.fetch_regions()

    region_data = bootstrap_api.get_region_by_name(region)
    provider_data = bootstrap_api.get_provider_by_name(region, provider)
    if not region_data or not provider_data:
        LOGGER.error(
            "Failed to resolve region/provider ids for entry %s",
            entry.entry_id,
        )
        return False

    # Resolve group for address if group is not provided
    group = entry.options.get(CONF_GROUP, entry.data.get(CONF_GROUP))
    street_id = entry.options.get(CONF_STREET_ID, entry.data.get(CONF_STREET_ID))
    house_id = entry.options.get(CONF_HOUSE_ID, entry.data.get(CONF_HOUSE_ID))
    if not group and street_id and house_id:
        group = await bootstrap_api.fetch_group_by_address(
            region_id=region_data["id"],
            provider_id=provider_data["id"],
            street_id=street_id,
            house_id=house_id,
        )

    # If group is not resolved, return error
    if not group:
        LOGGER.error("Missing group for entry %s", entry.entry_id)
        return False

    # Create new API instance with resolved group
    api = YasnoApi(
        region_id=region_data["id"],
        provider_id=provider_data["id"],
        group=group,
    )
    await api.fetch_regions()

    coordinator = YasnoOutagesCoordinator(hass, entry, api, group=group)
    entry.runtime_data = YasnoOutagesData(
        api=api,
        coordinator=coordinator,
        integration=async_get_loaded_integration(hass, entry.domain),
    )

    # First refresh
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(
    hass: HomeAssistant,
    entry: YasnoOutagesConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant,
    entry: YasnoOutagesConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    LOGGER.info("Unload entry: %s", entry)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
