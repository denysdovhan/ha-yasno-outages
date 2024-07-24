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
from .const import CONF_CITY, CONF_GROUP, DEFAULT_CITY, DEFAULT_GROUP, DOMAIN, NAME

LOGGER = logging.getLogger(__name__)

GROUP_PREFIX = "group_"


def extract_group_index(group: str) -> str:
    """Extract the group index from the group name."""
    return group[len(GROUP_PREFIX) :]


def get_config_value(
    entry: ConfigEntry | None,
    key: str,
    default: Any = None,
) -> Any:
    """Get a value from the config entry or default."""
    if entry is not None:
        return entry.options.get(key, entry.data.get(key, default))
    return default


def build_city_schema(
    api: YasnoOutagesApi,
    config_entry: ConfigEntry | None,
) -> vol.Schema:
    """Build the schema for the city selection step."""
    cities = api.get_cities()
    return vol.Schema(
        {
            vol.Required(
                CONF_CITY,
                default=get_config_value(config_entry, CONF_CITY, DEFAULT_CITY),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=cities,
                    translation_key="city",
                ),
            ),
        },
    )


def build_group_schema(
    api: YasnoOutagesApi,
    config_entry: ConfigEntry | None,
    data: dict,
) -> vol.Schema:
    """Build the schema for the group selection step."""
    city = data[CONF_CITY]
    groups = api.get_city_groups(city).keys()
    group_indexes = [extract_group_index(group) for group in groups]
    LOGGER.debug("Getting %s groups: %s", city, groups)

    return vol.Schema(
        {
            vol.Required(
                CONF_GROUP,
                default=get_config_value(config_entry, CONF_GROUP, DEFAULT_GROUP),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=group_indexes,
                    translation_key="group",
                ),
            ),
        },
    )


class YasnoOutagesOptionsFlow(OptionsFlow):
    """Handle options flow for Yasno Outages."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.api = YasnoOutagesApi()
        self.data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the city change."""
        if user_input is not None:
            LOGGER.debug("Updating options: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_group()

        await self.hass.async_add_executor_job(self.api.fetch_schedule)

        LOGGER.debug("Options: %s", self.config_entry.options)
        LOGGER.debug("Data: %s", self.config_entry.data)

        return self.async_show_form(
            step_id="init",
            data_schema=build_city_schema(api=self.api, config_entry=self.config_entry),
        )

    async def async_step_group(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the group change."""
        if user_input is not None:
            LOGGER.debug("User input: %s", user_input)
            self.data.update(user_input)
            return self.async_create_entry(title="", data=self.data)

        return self.async_show_form(
            step_id="group",
            data_schema=build_group_schema(
                api=self.api,
                config_entry=self.config_entry,
                data=self.data,
            ),
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
    def async_get_options_flow(config_entry: ConfigEntry) -> YasnoOutagesOptionsFlow:
        """Get the options flow for this handler."""
        return YasnoOutagesOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            LOGGER.debug("City selected: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_group()

        await self.hass.async_add_executor_job(self.api.fetch_schedule)

        return self.async_show_form(
            step_id="user",
            data_schema=build_city_schema(api=self.api, config_entry=None),
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

        return self.async_show_form(
            step_id="group",
            data_schema=build_group_schema(
                api=self.api,
                config_entry=None,
                data=self.data,
            ),
        )
