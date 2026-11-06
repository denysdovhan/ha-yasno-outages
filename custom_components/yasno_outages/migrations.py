"""Migrations for Yasno Outages config entries."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryError

from .config_flow import YasnoOutagesConfigFlow
from .const import (
    CONF_PROVIDER,
    CONF_PROVIDER_ID,
    CONF_REGION,
    CONF_REGION_ID,
    CONF_SERVICE,
    LOCATION_CONFIG_KEYS,
    PROVIDER_DTEK_FULL,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api import YasnoApi

LOGGER = logging.getLogger(__name__)


async def async_migrate_legacy_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate legacy configuration before setup resolves location IDs."""
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

    # Resolve legacy names during setup so API outages remain retryable.
    LOGGER.info("Entry %s now at version %s", entry.entry_id, entry.version)
    return True


def _resolve_region_provider_ids(
    entry: ConfigEntry,
    api: YasnoApi,
) -> tuple[int, int]:
    """Resolve saved IDs or legacy names using cached API metadata."""
    region_id = entry.options.get(CONF_REGION_ID, entry.data.get(CONF_REGION_ID))
    provider_id = entry.options.get(CONF_PROVIDER_ID, entry.data.get(CONF_PROVIDER_ID))
    if region_id is None or provider_id is None:
        region = entry.options.get(CONF_REGION, entry.data.get(CONF_REGION))
        provider = entry.options.get(CONF_PROVIDER, entry.data.get(CONF_PROVIDER))
        region_data = api.get_region_by_name(region)
        provider_data = api.get_provider_by_name(region, provider)
        if (
            region_data
            and provider_data is None
            and PROVIDER_DTEK_FULL in provider.upper()
        ):
            matches = [
                candidate
                for candidate in api.get_providers_for_region(region_data["id"])
                if PROVIDER_DTEK_FULL in candidate["name"].upper()
            ]
            provider_data = matches[0] if len(matches) == 1 else None
    else:
        region_data = api.get_region_by_id(region_id)
        provider_data = api.get_provider_by_id(region_id, provider_id)
    if not region_data or not provider_data:
        msg = "Region or provider no longer found; reconfigure integration entry"
        raise ConfigEntryError(msg)
    return region_data["id"], provider_data["id"]


@callback
def async_migrate_entry_data(
    hass: HomeAssistant,
    entry: ConfigEntry,
    api: YasnoApi,
) -> None:
    """Store the ID-based configuration with location fields in entry data."""
    region_id, provider_id = _resolve_region_provider_ids(entry, api)
    data = dict(entry.data)
    for key in LOCATION_CONFIG_KEYS:
        if key in entry.options:
            data[key] = entry.options[key]
    data.pop(CONF_REGION, None)
    data.pop(CONF_PROVIDER, None)
    data.update({CONF_REGION_ID: region_id, CONF_PROVIDER_ID: provider_id})
    options = {
        key: value
        for key, value in entry.options.items()
        if key not in LOCATION_CONFIG_KEYS
    }
    if (
        data != entry.data
        or options != entry.options
        or entry.version < YasnoOutagesConfigFlow.VERSION
        or entry.minor_version != YasnoOutagesConfigFlow.MINOR_VERSION
    ):
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            options=options,
            version=YasnoOutagesConfigFlow.VERSION,
            minor_version=YasnoOutagesConfigFlow.MINOR_VERSION,
        )
