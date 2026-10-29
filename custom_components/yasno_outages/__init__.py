"""Init file for Yasno Outages integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.loader import async_get_loaded_integration

from .api import YasnoApi, YasnoNotFoundError
from .const import (
    CONF_ADDRESS_GROUP,
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_PROVIDER,
    CONF_REGION,
    CONF_SERVICE,
    CONF_STREET_ID,
    LOCATION_CONFIG_KEYS,
)
from .coordinator import YasnoOutagesCoordinator
from .data import YasnoOutagesData
from .helpers import build_address_data
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


async def _async_resolve_group(
    hass: HomeAssistant,
    entry: YasnoOutagesConfigEntry,
    api: YasnoApi,
    *,
    region_id: int,
    provider_id: int,
) -> tuple[str | None, bool]:
    """Resolve the group and report whether the address needs repair."""
    config = {**entry.data, **entry.options}
    # A cached group must not turn address configuration into group configuration
    group = config.get(CONF_GROUP)
    street_id = config.get(CONF_STREET_ID)
    house_id = config.get(CONF_HOUSE_ID)
    cached_address = config.get(CONF_ADDRESS_GROUP)
    if street_id is None and house_id is None and cached_address is None:
        return group, False
    if not street_id or not house_id:
        msg = "Incomplete address; reconfigure integration entry"
        raise ConfigEntryError(msg)

    try:
        group = await api.fetch_group_by_address(
            region_id=region_id,
            provider_id=provider_id,
            street_id=street_id,
            house_id=house_id,
        )
    except YasnoNotFoundError as err:
        current_config = {**entry.data, **entry.options}
        if any(
            current_config.get(key) != config.get(key) for key in LOCATION_CONFIG_KEYS
        ):
            msg = "Configuration changed during address lookup; retry setup"
            raise ConfigEntryNotReady(msg) from err
        await async_create_stale_address_issue(hass, entry)
        address_data = build_address_data(
            config,
            region_id=region_id,
            provider_id=provider_id,
            group=group,
        )
        if (
            not isinstance(group, str)
            or not group.strip()
            or cached_address != address_data[CONF_ADDRESS_GROUP]
        ):
            msg = "Address no longer found; reconfigure integration entry"
            raise ConfigEntryError(msg) from err
        return group, True

    current_config = {**entry.data, **entry.options}
    if any(current_config.get(key) != config.get(key) for key in LOCATION_CONFIG_KEYS):
        msg = "Configuration changed during address lookup; retry setup"
        raise ConfigEntryNotReady(msg)
    if not isinstance(group, str) or not group.strip():
        group = None
    address_data = build_address_data(
        config,
        region_id=region_id,
        provider_id=provider_id,
        group=group,
    )
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, **address_data},
        options={
            key: value
            for key, value in entry.options.items()
            if key not in LOCATION_CONFIG_KEYS
        },
    )
    if not group:
        msg = "No group found for address; reconfigure integration entry"
        raise ConfigEntryError(msg)
    return group, False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YasnoOutagesConfigEntry,
) -> bool:
    """Set up a new entry."""
    LOGGER.info("Setup entry: %s", entry)

    # Legacy repairs saved group=None in data and options; reconfigure replaced
    # data with either a group and no address, or an address and no group key
    # Only remove those stale options; never reinterpret a validated cache
    if (
        entry.options.get(CONF_STREET_ID)
        and entry.options.get(CONF_HOUSE_ID)
        and CONF_GROUP in entry.options
        and entry.options[CONF_GROUP] is None
        and CONF_ADDRESS_GROUP not in entry.data
        and CONF_ADDRESS_GROUP not in entry.options
        and entry.data.get(CONF_REGION)
        and entry.data.get(CONF_PROVIDER)
        and (
            (
                isinstance(entry.data.get(CONF_GROUP), str)
                and entry.data[CONF_GROUP].strip()
                and CONF_STREET_ID not in entry.data
                and CONF_HOUSE_ID not in entry.data
            )
            or (
                CONF_GROUP not in entry.data
                and entry.data.get(CONF_STREET_ID)
                and entry.data.get(CONF_HOUSE_ID)
            )
        )
    ):
        hass.config_entries.async_update_entry(
            entry,
            options={
                key: value
                for key, value in entry.options.items()
                if key not in LOCATION_CONFIG_KEYS
            },
        )

    # Validate required keys are present
    config = {**entry.data, **entry.options}
    region = config.get(CONF_REGION)
    provider = config.get(CONF_PROVIDER)

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
    current_config = {**entry.data, **entry.options}
    if any(current_config.get(key) != config.get(key) for key in LOCATION_CONFIG_KEYS):
        msg = "Configuration changed during region lookup; retry setup"
        raise ConfigEntryNotReady(msg)

    region_data = bootstrap_api.get_region_by_name(region)
    provider_data = bootstrap_api.get_provider_by_name(region, provider)
    if not region_data or not provider_data:
        LOGGER.error(
            "Failed to resolve region/provider ids for entry %s",
            entry.entry_id,
        )
        return False

    group, stale_address = await _async_resolve_group(
        hass,
        entry,
        bootstrap_api,
        region_id=region_data["id"],
        provider_id=provider_data["id"],
    )

    # If group is not resolved, return error
    if not group:
        LOGGER.error("Missing group for entry %s", entry.entry_id)
        return False

    # Address resolution may have persisted the group and normalized options
    resolved_config = {**entry.data, **entry.options}

    # Create new API instance with resolved group
    api = YasnoApi(
        region_id=region_data["id"],
        provider_id=provider_data["id"],
        group=group,
    )
    await api.fetch_regions()

    if stale_address:
        # Surface fetch errors before the coordinator can substitute cached data
        await api.planned.fetch_planned_outages_data()

    coordinator = YasnoOutagesCoordinator(hass, entry, api, group=group)
    entry.runtime_data = YasnoOutagesData(
        api=api,
        coordinator=coordinator,
        integration=async_get_loaded_integration(hass, entry.domain),
    )

    # First refresh
    await coordinator.async_config_entry_first_refresh()

    current_config = {**entry.data, **entry.options}
    if any(
        current_config.get(key) != resolved_config.get(key)
        for key in LOCATION_CONFIG_KEYS
    ):
        await async_delete_stale_address_issue(hass, entry)
        msg = "Configuration changed during setup; retry setup"
        raise ConfigEntryNotReady(msg)

    if stale_address:
        if group not in api.planned.get_groups():
            msg = "Cached address group is no longer available; reconfigure entry"
            raise ConfigEntryError(msg)
        await async_create_stale_address_issue(hass, entry, using_cached_group=True)
        LOGGER.warning(
            "Address needs revalidation for entry %s; using its last validated group",
            entry.entry_id,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    if not stale_address:
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
