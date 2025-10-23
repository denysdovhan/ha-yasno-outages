"""Repairs for Yasno Outages integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_CITY, DOMAIN

LOGGER = logging.getLogger(__name__)


async def async_check_and_create_repair(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Check if repair is needed and create issue."""
    if CONF_CITY in entry.data or CONF_CITY in entry.options:
        LOGGER.info("Old config detected for entry %s, creating repair", entry.entry_id)
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"api_v1_to_v2_{entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="api_v1_to_v2",
        )
