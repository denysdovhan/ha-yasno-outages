"""Config flow for Yasno Outages integration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .api import YasnoApi
from .const import (
    CONF_ADDRESS_NAME,
    CONF_FILTER_PROBABLE,
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_PROVIDER,
    CONF_REGION,
    CONF_STATUS_ALL_DAY_EVENTS,
    CONF_STREET_ID,
    DOMAIN,
    YASNO_GROUP_URL,
)

LOGGER = logging.getLogger(__name__)

CONF_SETUP_MODE = "setup_mode"
CONF_STREET_QUERY = "street_query"
CONF_HOUSE_QUERY = "house_query"
CONF_STREET = "street"
CONF_HOUSE = "house"

SETUP_MODE_GROUP = "group"
SETUP_MODE_ADDRESS = "address"


def get_config_value(
    entry: ConfigEntry | None,
    key: str,
    default: Any = None,
) -> Any:
    """Get a value from the config entry or default."""
    if entry is not None:
        return entry.options.get(key, entry.data.get(key, default))
    return default


def build_entry_title(*, region: str, provider: str, group: str) -> str:
    """Build a descriptive title from region, provider, and group."""
    return f"Yasno {region} {provider} {group}"


def build_address_entry_title(
    *,
    region: str,
    street: str,
    house: str,
) -> str:
    """Build a descriptive title from region, provider, and address."""
    return f"Yasno {region} {street} {house}"


def build_region_schema(
    api: YasnoApi,
    config_entry: ConfigEntry | None,
) -> vol.Schema:
    """Build the schema for the region selection step."""
    regions = api.get_regions()
    region_options = [region["value"] for region in regions]
    return vol.Schema(
        {
            vol.Required(
                CONF_REGION,
                default=get_config_value(config_entry, CONF_REGION),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=region_options,
                    translation_key="region",
                ),
            ),
        },
    )


def build_provider_schema(
    api: YasnoApi,
    config_entry: ConfigEntry | None,
    data: dict,
) -> vol.Schema:
    """Build the schema for the provider selection step."""
    region = data[CONF_REGION]
    providers = api.get_providers_for_region(region)
    provider_options = [provider["name"] for provider in providers]

    return vol.Schema(
        {
            vol.Required(
                CONF_PROVIDER,
                default=get_config_value(config_entry, CONF_PROVIDER),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=provider_options,
                    translation_key="provider",
                ),
            ),
        },
    )


def build_group_schema(
    groups: list[str],
    config_entry: ConfigEntry | None,
) -> vol.Schema:
    """Build the schema for the group selection step."""
    return vol.Schema(
        {
            vol.Required(
                CONF_GROUP,
                default=get_config_value(config_entry, CONF_GROUP),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=groups,
                    translation_key="group",
                ),
            ),
        },
    )


def build_group_options_schema(
    groups: list[str],
    config_entry: ConfigEntry | None,
) -> vol.Schema:
    """Build the schema for the group and options selection step."""
    return vol.Schema(
        {
            vol.Required(
                CONF_GROUP,
                default=get_config_value(config_entry, CONF_GROUP),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=groups,
                    translation_key="group",
                ),
            ),
            vol.Required(
                CONF_FILTER_PROBABLE,
                default=get_config_value(
                    config_entry, CONF_FILTER_PROBABLE, default=True
                ),
            ): bool,
            vol.Required(
                CONF_STATUS_ALL_DAY_EVENTS,
                default=get_config_value(
                    config_entry,
                    CONF_STATUS_ALL_DAY_EVENTS,
                    default=True,
                ),
            ): bool,
        },
    )


def build_preferences_schema(
    config_entry: ConfigEntry | None,
) -> vol.Schema:
    """Build the schema for preferences."""
    return vol.Schema(
        {
            vol.Required(
                CONF_FILTER_PROBABLE,
                default=get_config_value(
                    config_entry, CONF_FILTER_PROBABLE, default=True
                ),
            ): bool,
            vol.Required(
                CONF_STATUS_ALL_DAY_EVENTS,
                default=get_config_value(
                    config_entry,
                    CONF_STATUS_ALL_DAY_EVENTS,
                    default=True,
                ),
            ): bool,
        },
    )


class YasnoOutagesOptionsFlow(OptionsFlow):
    """Handle options flow for Yasno Outages."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self.api = YasnoApi()
        self.data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the region change."""
        if user_input is not None:
            LOGGER.debug("Updating options: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_provider()

        await self.api.fetch_regions()

        LOGGER.debug("Options: %s", self.config_entry.options)
        LOGGER.debug("Data: %s", self.config_entry.data)

        return self.async_show_form(
            step_id="init",
            data_schema=build_region_schema(
                api=self.api, config_entry=self.config_entry
            ),
        )

    async def async_step_provider(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the provider change."""
        if user_input is not None:
            LOGGER.debug("Provider selected: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_group()

        return self.async_show_form(
            step_id="provider",
            data_schema=build_provider_schema(
                api=self.api,
                config_entry=self.config_entry,
                data=self.data,
            ),
        )

    async def async_step_group(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the group change."""
        if user_input is not None:
            LOGGER.debug("Group selected: %s", user_input)
            self.data.update(user_input)
            # Update entry title along with options
            updated_data = dict(self.config_entry.data)
            updated_data[CONF_REGION] = self.data[CONF_REGION]
            updated_data[CONF_PROVIDER] = self.data[CONF_PROVIDER]
            updated_data[CONF_GROUP] = self.data[CONF_GROUP]
            updated_data.pop(CONF_STREET_ID, None)
            updated_data.pop(CONF_HOUSE_ID, None)
            updated_data.pop(CONF_ADDRESS_NAME, None)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=build_entry_title(
                    region=self.data[CONF_REGION],
                    provider=self.data[CONF_PROVIDER],
                    group=self.data[CONF_GROUP],
                ),
                data=updated_data,
            )
            return self.async_create_entry(title="", data=self.data)

        # Fetch groups for the selected region/provider
        region = self.data[CONF_REGION]
        provider = self.data[CONF_PROVIDER]

        region_data = self.api.get_region_by_name(region)
        provider_data = self.api.get_provider_by_name(region, provider)
        groups = []
        if region_data and provider_data:
            temp_api = YasnoApi(
                region_id=region_data["id"],
                provider_id=provider_data["id"],
            )
            await temp_api.planned.fetch_planned_outages_data()
            groups = temp_api.planned.get_groups()

        return self.async_show_form(
            step_id="group",
            data_schema=build_group_options_schema(groups, self.config_entry),
            description_placeholders={"yasno_group_url": YASNO_GROUP_URL},
        )


class YasnoOutagesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yasno Outages."""

    VERSION = 2
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize config flow."""
        self.api = YasnoApi()
        self.data: dict[str, Any] = {}
        self._street_options: dict[str, str] = {}
        self._house_options: dict[str, str] = {}
        self._street_name = ""
        self._house_name = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> YasnoOutagesOptionsFlow:  # noqa: ARG004
        """Get the options flow for this handler."""
        return YasnoOutagesOptionsFlow()

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            LOGGER.debug("Region selected: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_provider()

        await self.api.fetch_regions()

        return self.async_show_form(
            step_id="user",
            data_schema=build_region_schema(api=self.api, config_entry=None),
        )

    async def async_step_provider(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the provider step."""
        if user_input is not None:
            LOGGER.debug("Provider selected: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_method()

        region = self.data[CONF_REGION]
        providers = self.api.get_providers_for_region(region)

        # If only one provider available, auto-select it and proceed
        if len(providers) == 1:
            provider_name = providers[0]["name"]
            LOGGER.debug("Auto-selecting only available provider: %s", provider_name)
            self.data[CONF_PROVIDER] = provider_name
            return await self.async_step_method()

        return self.async_show_form(
            step_id="provider",
            data_schema=build_provider_schema(
                api=self.api,
                config_entry=None,
                data=self.data,
            ),
        )

    async def async_step_method(
        self,
        user_input: dict | None = None,  # noqa: ARG002
    ) -> ConfigFlowResult:
        """Handle setup method selection."""
        return self.async_show_menu(
            step_id="method",
            menu_options=[SETUP_MODE_GROUP, SETUP_MODE_ADDRESS],
        )

    async def async_step_address(
        self,
        user_input: dict | None = None,  # noqa: ARG002
    ) -> ConfigFlowResult:
        """Handle address setup method."""
        return await self.async_step_street_query()

    async def async_step_street_query(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle street search query."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = user_input[CONF_STREET_QUERY].strip()
            if not query:
                errors["base"] = "street_query_required"
            else:
                region_id, provider_id = self._get_region_provider_ids()
                try:
                    streets = await self.api.fetch_streets(
                        region_id=region_id,
                        provider_id=provider_id,
                        query=query,
                    )
                except Exception:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
                else:
                    if not streets:
                        errors["base"] = "no_streets"
                    else:
                        self._street_options = {
                            str(item["id"]): item["value"] for item in streets
                        }
                        return await self.async_step_street()

        return self.async_show_form(
            step_id="street_query",
            data_schema=vol.Schema({vol.Required(CONF_STREET_QUERY): str}),
            errors=errors,
        )

    async def async_step_street(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle street selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            street_id = user_input[CONF_STREET]
            street_name = self._street_options.get(street_id)
            if not street_name:
                errors["base"] = "no_streets"
            else:
                self.data[CONF_STREET_ID] = int(street_id)
                self._street_name = street_name
                return await self.async_step_house_query()

        return self.async_show_form(
            step_id="street",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STREET): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": key, "label": value}
                                for key, value in self._street_options.items()
                            ]
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_house(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle house selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            house_id = user_input[CONF_HOUSE]
            house_name = self._house_options.get(house_id)
            if not house_name:
                errors["base"] = "no_houses"
            else:
                self.data[CONF_HOUSE_ID] = int(house_id)
                self._house_name = house_name
                region_id, provider_id = self._get_region_provider_ids()
                street_id = self.data.get(CONF_STREET_ID)
                try:
                    group = await self.api.fetch_group_by_address(
                        region_id=region_id,
                        provider_id=provider_id,
                        street_id=street_id,
                        house_id=self.data.get(CONF_HOUSE_ID),
                    )
                except Exception:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
                else:
                    if not group:
                        errors["base"] = "no_group"
                    else:
                        return await self.async_step_preferences()
        return self.async_show_form(
            step_id="house",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOUSE): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": key, "label": value}
                                for key, value in self._house_options.items()
                            ]
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_house_query(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle house search query."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = user_input[CONF_HOUSE_QUERY].strip()
            if not query:
                errors["base"] = "house_query_required"
            else:
                region_id, provider_id = self._get_region_provider_ids()
                street_id = self.data.get(CONF_STREET_ID)
                try:
                    houses = await self.api.fetch_houses(
                        region_id=region_id,
                        provider_id=provider_id,
                        street_id=street_id,
                        query=query,
                    )
                except Exception:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
                else:
                    if not houses:
                        errors["base"] = "no_houses"
                    else:
                        self._house_options = {
                            str(item["id"]): item["value"] for item in houses
                        }
                        return await self.async_step_house()

        return self.async_show_form(
            step_id="house_query",
            data_schema=vol.Schema({vol.Required(CONF_HOUSE_QUERY): str}),
            errors=errors,
        )

    async def async_step_preferences(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle preferences before entry creation."""
        if user_input is not None:
            self.data.update(user_input)
            if self.data.get(CONF_GROUP):
                title = build_entry_title(
                    region=self.data[CONF_REGION],
                    provider=self.data[CONF_PROVIDER],
                    group=self.data[CONF_GROUP],
                )
                data = {
                    CONF_REGION: self.data[CONF_REGION],
                    CONF_PROVIDER: self.data[CONF_PROVIDER],
                    CONF_GROUP: self.data[CONF_GROUP],
                }
            else:
                title = build_address_entry_title(
                    region=self.data[CONF_REGION],
                    street=self._street_name,
                    house=self._house_name,
                )
                data = {
                    CONF_REGION: self.data[CONF_REGION],
                    CONF_PROVIDER: self.data[CONF_PROVIDER],
                    CONF_STREET_ID: self.data[CONF_STREET_ID],
                    CONF_HOUSE_ID: self.data[CONF_HOUSE_ID],
                    CONF_ADDRESS_NAME: f"{self._street_name} {self._house_name}",
                }

            data.update(
                {
                    CONF_FILTER_PROBABLE: self.data[CONF_FILTER_PROBABLE],
                    CONF_STATUS_ALL_DAY_EVENTS: self.data[CONF_STATUS_ALL_DAY_EVENTS],
                }
            )

            return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="preferences",
            data_schema=build_preferences_schema(None),
        )

    def _get_region_provider_ids(self) -> tuple[int | None, int | None]:
        """Return region and provider IDs from selected names."""
        region = self.data[CONF_REGION]
        provider = self.data[CONF_PROVIDER]
        region_data = self.api.get_region_by_name(region)
        provider_data = self.api.get_provider_by_name(region, provider)
        return (
            region_data["id"] if region_data else None,
            provider_data["id"] if provider_data else None,
        )

    async def async_step_group(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the group step."""
        if user_input is not None:
            LOGGER.debug("User input: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_preferences()

        # Fetch groups for the selected region/provider
        region = self.data[CONF_REGION]
        provider = self.data[CONF_PROVIDER]

        region_data = self.api.get_region_by_name(region)
        provider_data = self.api.get_provider_by_name(region, provider)
        groups = []
        if region_data and provider_data:
            temp_api = YasnoApi(
                region_id=region_data["id"],
                provider_id=provider_data["id"],
            )
            await temp_api.planned.fetch_planned_outages_data()
            groups = temp_api.planned.get_groups()

        return self.async_show_form(
            step_id="group",
            data_schema=build_group_schema(groups, None),
            description_placeholders={"yasno_group_url": YASNO_GROUP_URL},
        )
