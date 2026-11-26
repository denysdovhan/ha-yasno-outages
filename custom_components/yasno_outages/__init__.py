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
    CONF_ADDRESS_NAME,
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_HOUSE_NAME,
    CONF_PROVIDER,
    CONF_PROVIDER_ID,
    CONF_REGION,
    CONF_REGION_ID,
    CONF_STREET_ID,
    CONF_STREET_NAME,
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


def _saved_address_names(entry: ConfigEntry) -> tuple[str, str] | None:
    """Return saved street/house names, or split the legacy combined address."""
    street_name = entry.data.get(CONF_STREET_NAME)
    house_name = entry.data.get(CONF_HOUSE_NAME)
    if street_name and house_name:
        return street_name, house_name
    # Legacy entries have only "<street> <house>"; a wrong split fails to match.
    combined = entry.data.get(CONF_ADDRESS_NAME) or ""
    street_name, _, house_name = combined.rpartition(" ")
    if street_name and house_name:
        return street_name, house_name
    return None


async def _async_reresolve_address(
    hass: HomeAssistant,
    entry: ConfigEntry,
    api: YasnoApi,
    region_id: int,
    provider_id: int,
) -> str | None:
    """Refresh stale street/house IDs from saved names; return the group."""
    names = _saved_address_names(entry)
    if names is None:
        return None
    street_name, house_name = names
    try:
        ids = await api.find_address_ids(
            region_id, provider_id, street_name, house_name
        )
        if ids is None:
            return None
        street_id, house_id = ids
        group = await api.fetch_group_by_address(
            region_id=region_id,
            provider_id=provider_id,
            street_id=street_id,
            house_id=house_id,
        )
    except YasnoNotFoundError:
        return None
    except (YasnoApiError, TimeoutError) as err:
        raise ConfigEntryNotReady from err

    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_STREET_ID: street_id,
            CONF_HOUSE_ID: house_id,
            CONF_STREET_NAME: street_name,
            CONF_HOUSE_NAME: house_name,
        },
    )
    LOGGER.warning(
        "Address IDs changed upstream; re-resolved %s %s", street_name, house_name
    )
    return group


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
            group = await _async_reresolve_address(
                hass, entry, bootstrap_api, region_id, provider_id
            )
            if not group:
                await async_create_stale_address_issue(hass, entry)
                msg = "Address no longer found; reconfigure integration entry"
                raise ConfigEntryError(msg) from err
        except (YasnoApiError, TimeoutError) as err:
            raise ConfigEntryNotReady from err

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
