"""Init file for Yasno Outages integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.loader import async_get_loaded_integration

from .api import YasnoApi, YasnoApiError, YasnoNotFoundError
from .const import (
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_PROVIDER,
    CONF_PROVIDER_ID,
    CONF_REGION,
    CONF_REGION_ID,
    CONF_STREET_ID,
)
from .coordinator import YasnoOutagesCoordinator, create_schedule_store
from .data import YasnoOutagesData
from .migrations import async_migrate_entry_data, async_migrate_legacy_entry
from .repairs import (
    async_check_and_create_repair,
    async_create_stale_address_issue,
    async_delete_stale_address_issue,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .data import YasnoOutagesConfigEntry

LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry to new version."""
    return await async_migrate_legacy_entry(hass, entry)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YasnoOutagesConfigEntry,
) -> bool:
    """Set up a new entry."""
    LOGGER.info("Setup entry: %s", entry)

    # Validate required keys are present
    region = entry.options.get(CONF_REGION, entry.data.get(CONF_REGION))
    provider = entry.options.get(CONF_PROVIDER, entry.data.get(CONF_PROVIDER))
    region_id = entry.options.get(CONF_REGION_ID, entry.data.get(CONF_REGION_ID))
    provider_id = entry.options.get(CONF_PROVIDER_ID, entry.data.get(CONF_PROVIDER_ID))

    # Check for other issues (like old API format)
    await async_check_and_create_repair(hass, entry)

    if (region_id is None or provider_id is None) and (not region or not provider):
        LOGGER.error(
            "Missing required keys for entry %s: region=%s, provider=%s",
            entry.entry_id,
            region,
            provider,
        )
        return False

    # Setup API for resolving region and provider ids
    bootstrap_api = YasnoApi()
    try:
        await bootstrap_api.fetch_regions()
    except (YasnoApiError, TimeoutError) as err:
        raise ConfigEntryNotReady from err

    try:
        async_migrate_entry_data(hass, entry, bootstrap_api)
    except ConfigEntryError:
        if not any(entry.async_get_active_flows(hass, {SOURCE_RECONFIGURE})):
            await hass.config_entries.flow.async_init(
                entry.domain,
                context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
            )
        raise

    region_id = entry.data[CONF_REGION_ID]
    provider_id = entry.data[CONF_PROVIDER_ID]

    # Resolve group for address if group is not provided
    group = entry.data.get(CONF_GROUP)
    street_id = entry.data.get(CONF_STREET_ID)
    house_id = entry.data.get(CONF_HOUSE_ID)
    if not group and street_id and house_id:
        try:
            group = await bootstrap_api.fetch_group_by_address(
                region_id=region_id,
                provider_id=provider_id,
                street_id=street_id,
                house_id=house_id,
            )
        except YasnoNotFoundError as err:
            await async_create_stale_address_issue(hass, entry)
            msg = "Address no longer found; reconfigure integration entry"
            raise ConfigEntryError(msg) from err

    # If group is not resolved, return error
    if not group:
        LOGGER.error("Missing group for entry %s", entry.entry_id)
        return False

    # Create new API instance with resolved group
    api = YasnoApi(
        region_id=region_id,
        provider_id=provider_id,
        group=group,
    )
    api.regions_data = bootstrap_api.regions_data

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
    await async_delete_stale_address_issue(hass, entry)
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


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the entry's stored schedule."""
    await create_schedule_store(hass, entry.entry_id).async_remove()
