"""Repairs for Yasno Outages integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_PROVIDER, DOMAIN

LOGGER = logging.getLogger(__name__)


async def async_check_and_create_repair(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Check if repair is needed and create issue."""
    if "city" in entry.data or "city" in entry.options:
        LOGGER.info("Old config detected for entry %s, creating repair", entry.entry_id)
        LOGGER.debug("Old config: %s", entry.data)
        LOGGER.debug("Old options: %s", entry.options)
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"api_v1_to_v2_{entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="api_v1_to_v2",
        )

    # Auto-migrate service -> provider field rename
    updated_data = dict(entry.data)
    updated_options = dict(entry.options)
    config_updated = False

    if "service" in updated_data:
        updated_data[CONF_PROVIDER] = updated_data.pop("service")
        config_updated = True
        LOGGER.info(
            "Migrated 'service' to 'provider' in data for entry %s", entry.entry_id
        )

    if config_updated:
        hass.config_entries.async_update_entry(
            entry, data=updated_data, options=updated_options
        )
