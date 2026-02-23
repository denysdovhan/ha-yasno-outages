"""Repairs for Yasno Outages integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.helpers import issue_registry as ir

from .api import YasnoApi
from .config_flow import (
    build_address_entry_title,
    build_house_query_schema,
    build_house_schema,
    build_lookup_options,
    build_street_query_schema,
    build_street_schema,
)
from .const import (
    CONF_ADDRESS_NAME,
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_PROVIDER,
    CONF_REGION,
    CONF_STEP_HOUSE,
    CONF_STEP_HOUSE_QUERY,
    CONF_STEP_STREET,
    CONF_STEP_STREET_QUERY,
    CONF_STREET_ID,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResult

LOGGER = logging.getLogger(__name__)


class StaleAddressRepairFlow(RepairsFlow):
    """Repair flow to reselect street/house for stale address ids."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the stale-address repair flow."""
        self._entry = entry
        self._api = YasnoApi()
        self._region_id: int | None = None
        self._provider_id: int | None = None
        self._street_options: dict[str, str] = {}
        self._house_options: dict[str, str] = {}
        self._street_name = ""
        self._house_name = ""
        self._street_id: int | None = None

    def _get_config_value(self, key: str) -> Any:
        """Read value from options first, then data."""
        return self._entry.options.get(key, self._entry.data.get(key))

    async def _resolve_region_provider_ids(self) -> bool:
        """Resolve selected region/provider names into ids."""
        if self._region_id and self._provider_id:
            return True

        region = self._get_config_value(CONF_REGION)
        provider = self._get_config_value(CONF_PROVIDER)
        if not region or not provider:
            return False

        await self._api.fetch_regions()
        region_data = self._api.get_region_by_name(region)
        provider_data = self._api.get_provider_by_name(region, provider)
        if not region_data or not provider_data:
            return False

        self._region_id = region_data["id"]
        self._provider_id = provider_data["id"]
        return True

    async def async_step_init(
        self,
        user_input: dict[str, str] | None = None,  # noqa: ARG002
    ) -> FlowResult:
        """Handle the first step of repair flow."""
        return await self.async_step_street_query()

    async def async_step_street_query(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle street search query."""
        errors: dict[str, str] = {}

        try:
            resolved = await self._resolve_region_provider_ids()
        except Exception:  # noqa: BLE001
            resolved = False
        if not resolved:
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="street_query",
                data_schema=build_street_query_schema(),
                errors=errors,
                description_placeholders={"entry_title": self._entry.title},
            )

        if user_input is not None:
            query = user_input[CONF_STEP_STREET_QUERY].strip()
            if not query:
                errors["base"] = "street_query_required"
            else:
                try:
                    streets = await self._api.fetch_streets(
                        region_id=self._region_id,
                        provider_id=self._provider_id,
                        query=query,
                    )
                except Exception:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
                else:
                    if not streets:
                        errors["base"] = "no_streets"
                    else:
                        if len(streets) == 1:
                            street = streets[0]
                            self._street_id = street["id"]
                            self._street_name = street["value"]
                            return await self.async_step_house_query()
                        self._street_options = build_lookup_options(streets)
                        return await self.async_step_street()

        return self.async_show_form(
            step_id="street_query",
            data_schema=build_street_query_schema(),
            errors=errors,
            description_placeholders={"entry_title": self._entry.title},
        )

    async def async_step_street(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle street selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            street_id = user_input[CONF_STEP_STREET]
            street_name = self._street_options.get(street_id)
            if not street_name:
                errors["base"] = "no_streets"
            else:
                self._street_id = int(street_id)
                self._street_name = street_name
                return await self.async_step_house_query()

        return self.async_show_form(
            step_id="street",
            data_schema=build_street_schema(self._street_options),
            errors=errors,
            description_placeholders={"entry_title": self._entry.title},
        )

    async def async_step_house_query(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle house search query."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = user_input[CONF_STEP_HOUSE_QUERY].strip()
            if not query:
                errors["base"] = "house_query_required"
            else:
                try:
                    houses = await self._api.fetch_houses(
                        region_id=self._region_id,
                        provider_id=self._provider_id,
                        street_id=self._street_id,
                        query=query,
                    )
                except Exception:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
                else:
                    if not houses:
                        errors["base"] = "no_houses"
                    else:
                        self._house_options = build_lookup_options(houses)
                        return await self.async_step_house()

        return self.async_show_form(
            step_id="house_query",
            data_schema=build_house_query_schema(),
            errors=errors,
            description_placeholders={"entry_title": self._entry.title},
        )

    async def async_step_house(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle house selection and save repaired config."""
        errors: dict[str, str] = {}

        if user_input is not None:
            house_id = user_input[CONF_STEP_HOUSE]
            house_name = self._house_options.get(house_id)
            if not house_name:
                errors["base"] = "no_houses"
            else:
                self._house_name = house_name
                resolved_house_id = int(house_id)
                try:
                    group = await self._api.fetch_group_by_address(
                        region_id=self._region_id,
                        provider_id=self._provider_id,
                        street_id=self._street_id,
                        house_id=resolved_house_id,
                    )
                except Exception:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
                else:
                    if not group:
                        errors["base"] = "no_group"
                    else:
                        updated_data = dict(self._entry.data)
                        updated_data.update(
                            {
                                CONF_STREET_ID: self._street_id,
                                CONF_HOUSE_ID: resolved_house_id,
                                CONF_ADDRESS_NAME: (
                                    f"{self._street_name} {self._house_name}"
                                ),
                                CONF_GROUP: None,
                            }
                        )
                        region = self._get_config_value(CONF_REGION)
                        title = build_address_entry_title(
                            region=region if isinstance(region, str) else "",
                            street=self._street_name,
                            house=self._house_name,
                        )
                        updated_options = dict(self._entry.options)
                        updated_options.update(
                            {
                                CONF_STREET_ID: self._street_id,
                                CONF_HOUSE_ID: resolved_house_id,
                                CONF_ADDRESS_NAME: (
                                    f"{self._street_name} {self._house_name}"
                                ),
                                CONF_GROUP: None,
                            }
                        )
                        self.hass.config_entries.async_update_entry(
                            self._entry,
                            data=updated_data,
                            options=updated_options,
                            title=title,
                        )
                        self.hass.config_entries.async_schedule_reload(
                            self._entry.entry_id
                        )
                        return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="house",
            data_schema=build_house_schema(self._house_options),
            errors=errors,
            description_placeholders={"entry_title": self._entry.title},
        )


async def async_create_stale_address_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Create repair issue for stale address identifiers."""
    issue_id = f"stale_address_ids_{entry.entry_id}"
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="stale_address_ids",
        translation_placeholders={
            "entry_title": entry.title or "Yasno Outages",
        },
        data={"entry_id": entry.entry_id},
    )


async def async_delete_stale_address_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Delete stale-address issue if present."""
    issue_id = f"stale_address_ids_{entry.entry_id}"
    ir.async_delete_issue(hass, DOMAIN, issue_id)


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


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None = None,  # noqa: ARG001
) -> RepairsFlow:
    """Create a repairs flow for the given issue."""
    if issue_id.startswith("stale_address_ids_"):
        entry_id = issue_id.removeprefix("stale_address_ids_")
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry:
            return StaleAddressRepairFlow(entry)
    return ConfirmRepairFlow()
