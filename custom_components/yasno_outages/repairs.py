"""Repairs for Yasno Outages integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.repairs import RepairsFlow

from .const import CONF_PROVIDER, CONF_REGION, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResult

LOGGER = logging.getLogger(__name__)


async def async_check_and_create_repair(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Check if repair is needed and create issue."""
    # Check for missing required configuration keys
    region = entry.options.get(CONF_REGION, entry.data.get(CONF_REGION))
    provider = entry.options.get(CONF_PROVIDER, entry.data.get(CONF_PROVIDER))

    if not region or not provider:
        LOGGER.info(
            "Missing required keys for entry %s, creating repair",
            entry.entry_id,
        )
        LOGGER.debug("region=%s, provider=%s", region, provider)
        LOGGER.debug("data=%s, options=%s", entry.data, entry.options)

        ir.async_create_issue(
            hass,
            DOMAIN,
            f"missing_config_{entry.entry_id}",
            is_fixable=False,
            is_persistent=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="missing_config",
            translation_placeholders={
                "entry_id": entry.entry_id,
                "entry_title": entry.title or "Yasno Outages",
                "edit": (
                    "/config/integrations/integration/yasno_outages"
                    f"#config_entry={entry.entry_id}"
                ),
            },
        )
    else:
        # Delete the issue if it exists (config is now complete)
        ir.async_delete_issue(hass, DOMAIN, f"missing_config_{entry.entry_id}")


class YasnoOutagesRepairsFlow(RepairsFlow):
    """Repairs flow placeholder; issues are informational only."""

    def __init__(self, issue_id: str) -> None:
        """Store issue id."""
        self._issue_id = issue_id

    async def async_step_init(self) -> FlowResult:
        """Abort because nothing to fix from UI side."""
        return self.async_abort(reason="not_supported")


async def async_create_fix_flow(
    hass: HomeAssistant,  # noqa: ARG001
    issue_id: str,
) -> RepairsFlow:
    """Create a repairs flow for the given issue."""
    return YasnoOutagesRepairsFlow(issue_id)
