"""Repairs for Yasno outages integration."""

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from .config_flow import build_group_schema
from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import YasnoOutagesCoordinator

LOGGER = logging.getLogger(__name__)

ID_GROUP_NOT_FOUND = "group_not_found"


def group_not_found_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
    city: str,
    group: str,
) -> None:
    """Raise an issue for a group not found."""
    ir.async_create_issue(
        hass=hass,
        domain=DOMAIN,
        issue_id=f"{ID_GROUP_NOT_FOUND}_{city}_{group}",
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="group_not_found",
        translation_placeholders={
            "group": group,
            "city": city,
        },
        data={"entry_id": entry.entry_id},
    )


class GroupNotFoundRepairsFlow(RepairsFlow):
    """Repairs flow for group not found."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the repair flow."""
        self.hass = hass
        LOGGER.debug("entry: %s", entry)
        self.entry = entry
        self.coordinator: YasnoOutagesCoordinator = entry.runtime_data
        self.data: dict[str, Any] = entry.options

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Handle the first step of the repair flow."""
        if user_input is not None:
            self.data.update(user_input)
        return await self.async_step_select_group()

    async def async_step_select_group(
        self,
        user_input: dict | None = None,
    ) -> FlowResult:
        """Handle the step to select a group."""
        if user_input is not None:
            LOGGER.debug("New selected group: %s", user_input)
            self.data.update(user_input)
            self.hass.config_entries.async_update_entry(self.entry, options=self.data)
            await self.hass.config_entries.async_reload(self.entry.entry_id)
            return self.async_create_entry(title="", data=self.data)

        return self.async_show_form(
            step_id="select_group",
            data_schema=build_group_schema(
                api=self.coordinator.api,
                config_entry=self.entry,
                data=self.entry.options,
            ),
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if (  # noqa: SIM102
        data is not None
        and "entry_id" in data
        and (entry := hass.config_entries.async_get_entry(data["entry_id"]))
    ):
        if issue_id.startswith(ID_GROUP_NOT_FOUND):
            return GroupNotFoundRepairsFlow(hass, entry)
        #
        # More repair flows can be added here
        #
    return ConfirmRepairFlow()
