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
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
)

from .api import YasnoOutagesApi
from .const import (
    CONF_GROUP,
    CONF_PROVIDER,
    CONF_REGION,
    DOMAIN,
    NAME,
)

LOGGER = logging.getLogger(__name__)


def get_config_value(
    entry: ConfigEntry | None,
    key: str,
    default: Any = None,
) -> Any:
    """Get a value from the config entry or default."""
    if entry is not None:
        return entry.options.get(key, entry.data.get(key, default))
    return default


def build_region_schema(
    api: YasnoOutagesApi,
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
    api: YasnoOutagesApi,
    config_entry: ConfigEntry | None,
    data: dict,
) -> vol.Schema:
    """Build the schema for the provider selection step."""
    region = data[CONF_REGION]
    providers = api.get_providers_for_region(region)
    provider_options = [_["name"] for _ in providers]

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


class YasnoOutagesOptionsFlow(OptionsFlow):
    """Handle options flow for Yasno Outages."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self.api = YasnoOutagesApi()
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
            return self.async_create_entry(title="", data=self.data)

        # Fetch groups for the selected region/provider
        region = self.data[CONF_REGION]
        provider = self.data[CONF_PROVIDER]

        region_data = self.api.get_region_by_name(region)
        provider_data = self.api.get_provider_by_name(region, provider)
        groups = []
        if region_data and provider_data:
            temp_api = YasnoOutagesApi(
                region_id=region_data["id"],
                provider_id=provider_data["id"],
            )
            await temp_api.fetch_planned_outages_data()
            groups = temp_api.get_groups()

        return self.async_show_form(
            step_id="group",
            data_schema=build_group_schema(groups, self.config_entry),
        )


class YasnoOutagesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yasno Outages."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self.api = YasnoOutagesApi()
        self.data: dict[str, Any] = {}

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
            return await self.async_step_group()

        region = self.data[CONF_REGION]
        providers = self.api.get_providers_for_region(region)

        # If only one provider available, auto-select it and proceed
        if len(providers) == 1:
            provider_name = providers[0]["name"]
            LOGGER.debug("Auto-selecting only available provider: %s", provider_name)
            self.data[CONF_PROVIDER] = provider_name
            return await self.async_step_group()

        return self.async_show_form(
            step_id="provider",
            data_schema=build_provider_schema(
                api=self.api,
                config_entry=None,
                data=self.data,
            ),
        )

    async def async_step_group(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the group step."""
        if user_input is not None:
            LOGGER.debug("User input: %s", user_input)
            self.data.update(user_input)
            return self.async_create_entry(title=NAME, data=self.data)

        # Fetch groups for the selected region/provider
        region = self.data[CONF_REGION]
        provider = self.data[CONF_PROVIDER]

        region_data = self.api.get_region_by_name(region)
        provider_data = self.api.get_provider_by_name(region, provider)
        groups = []
        if region_data and provider_data:
            temp_api = YasnoOutagesApi(
                region_id=region_data["id"],
                provider_id=provider_data["id"],
            )
            await temp_api.fetch_planned_outages_data()
            groups = temp_api.get_groups()

        return self.async_show_form(
            step_id="group",
            data_schema=build_group_schema(groups, None),
        )
