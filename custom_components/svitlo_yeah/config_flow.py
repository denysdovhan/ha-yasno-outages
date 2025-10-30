"""Config flow for Svitlo Yeah integration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
)

from .api.dtek import DtekAPI
from .api.yasno import YasnoApi
from .const import (
    CONF_GROUP,
    CONF_PROVIDER,
    CONF_PROVIDER_TYPE,
    CONF_REGION,
    DOMAIN,
    NAME,
    PROVIDER_TYPE_DTEK,
    PROVIDER_TYPE_YASNO,
    REGION_SELECTION_DTEK_KEY,
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
    api_yasno: YasnoApi,
    config_entry: ConfigEntry | None,
) -> vol.Schema:
    """Build the schema for the region selection step."""
    yasno_regions = api_yasno.get_yasno_regions()
    region_options = [region["value"] for region in yasno_regions]
    region_options.append(REGION_SELECTION_DTEK_KEY)
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


def build_yasno_provider_schema(
    api_yasno: YasnoApi,
    config_entry: ConfigEntry | None,
    data: dict,
) -> vol.Schema:
    """Build the schema for the provider selection step."""
    yasno_region = data[CONF_REGION]
    providers = api_yasno.get_yasno_providers_for_region(yasno_region)
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


class YasnoOutagesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Svitlo Yeah."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self.api = YasnoApi()
        self.data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            LOGGER.debug("Region selected: %s", user_input)
            self.data.update(user_input)

            if user_input[CONF_REGION] == REGION_SELECTION_DTEK_KEY:
                self.data[CONF_PROVIDER_TYPE] = PROVIDER_TYPE_DTEK
                # noinspection PyTypeChecker
                return await self.async_step_dtek_group()

            self.data[CONF_PROVIDER_TYPE] = PROVIDER_TYPE_YASNO
            # noinspection PyTypeChecker
            return await self.async_step_provider()

        await self.api.fetch_yasno_regions()

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id="user",
            data_schema=build_region_schema(api_yasno=self.api, config_entry=None),
        )

    async def async_step_provider(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the provider step."""
        if user_input is not None:
            LOGGER.debug("Provider selected: %s", user_input)
            self.data.update(user_input)
            # noinspection PyTypeChecker
            return await self.async_step_group()

        region = self.data[CONF_REGION]
        providers = self.api.get_yasno_providers_for_region(region)

        # If only one provider available, auto-select it and proceed
        if len(providers) == 1:
            provider_name = providers[0]["name"]
            LOGGER.debug("Auto-selecting only available provider: %s", provider_name)
            self.data[CONF_PROVIDER] = provider_name
            # noinspection PyTypeChecker
            return await self.async_step_group()

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id="provider",
            data_schema=build_yasno_provider_schema(
                api_yasno=self.api,
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
            # noinspection PyTypeChecker
            return self.async_create_entry(title=NAME, data=self.data)

        # Fetch groups for the selected region/provider
        yasno_region = self.data[CONF_REGION]
        provider = self.data[CONF_PROVIDER]

        region_data = self.api.get_region_by_name(yasno_region)
        provider_data = self.api.get_yasno_provider_by_name(yasno_region, provider)
        groups = []
        if region_data and provider_data:
            temp_api = YasnoApi(
                region_id=region_data["id"],
                provider_id=provider_data["id"],
            )
            await temp_api.fetch_planned_outage_data()
            groups = temp_api.get_yasno_groups()

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id="group",
            data_schema=build_group_schema(groups, None),
        )

    async def async_step_dtek_group(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the DTEK group step."""
        if user_input is not None:
            LOGGER.debug("DTEK group selected: %s", user_input)
            self.data.update(user_input)
            # noinspection PyTypeChecker
            return self.async_create_entry(title=NAME, data=self.data)

        dtek_api = DtekAPI()
        await dtek_api.fetch_data()
        groups = dtek_api.get_dtek_region_groups()

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id="dtek_group",
            data_schema=build_group_schema(groups, None),
        )
