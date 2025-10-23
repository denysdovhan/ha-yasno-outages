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
    CONF_CITY,
    CONF_GROUP,
    CONF_SERVICE,
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


def build_city_schema(
    api: YasnoOutagesApi,
    config_entry: ConfigEntry | None,
) -> vol.Schema:
    """Build the schema for the city (region) selection step."""
    regions = api.get_regions()
    city_options = [region["value"] for region in regions]
    return vol.Schema(
        {
            vol.Required(
                CONF_CITY,
                default=get_config_value(config_entry, CONF_CITY),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=city_options,
                    translation_key="city",
                ),
            ),
        },
    )


def build_service_schema(
    api: YasnoOutagesApi,
    config_entry: ConfigEntry | None,
    data: dict,
) -> vol.Schema:
    """Build the schema for the service selection step."""
    city = data[CONF_CITY]
    services = api.get_services_for_region(city)
    service_options = [service["name"] for service in services]

    return vol.Schema(
        {
            vol.Required(
                CONF_SERVICE,
                default=get_config_value(config_entry, CONF_SERVICE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=service_options,
                    translation_key="service",
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
        """Handle the city (region) change."""
        if user_input is not None:
            LOGGER.debug("Updating options: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_service()

        await self.api.fetch_regions()

        LOGGER.debug("Options: %s", self.config_entry.options)
        LOGGER.debug("Data: %s", self.config_entry.data)

        return self.async_show_form(
            step_id="init",
            data_schema=build_city_schema(api=self.api, config_entry=self.config_entry),
        )

    async def async_step_service(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the service change."""
        if user_input is not None:
            LOGGER.debug("Service selected: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_group()

        return self.async_show_form(
            step_id="service",
            data_schema=build_service_schema(
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

        # Fetch groups for the selected city/service
        city = self.data[CONF_CITY]
        service = self.data[CONF_SERVICE]

        region_data = self.api.get_region_by_name(city)
        service_data = self.api.get_service_by_name(city, service)
        groups = []
        if region_data and service_data:
            temp_api = YasnoOutagesApi(
                region_id=region_data["id"],
                service_id=service_data["id"],
            )
            await temp_api.fetch_outages_data()
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
    def async_get_options_flow(config_entry: ConfigEntry) -> YasnoOutagesOptionsFlow:
        """Get the options flow for this handler."""
        return YasnoOutagesOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            LOGGER.debug("City selected: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_service()

        await self.api.fetch_regions()

        return self.async_show_form(
            step_id="user",
            data_schema=build_city_schema(api=self.api, config_entry=None),
        )

    async def async_step_service(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the service step."""
        if user_input is not None:
            LOGGER.debug("Service selected: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_group()

        city = self.data[CONF_CITY]
        services = self.api.get_services_for_region(city)

        # If only one service available, auto-select it and proceed
        if len(services) == 1:
            service_name = services[0]["name"]
            LOGGER.debug("Auto-selecting only available service: %s", service_name)
            self.data[CONF_SERVICE] = service_name
            return await self.async_step_group()

        return self.async_show_form(
            step_id="service",
            data_schema=build_service_schema(
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

        # Fetch groups for the selected city/service
        city = self.data[CONF_CITY]
        service = self.data[CONF_SERVICE]

        region_data = self.api.get_region_by_name(city)
        service_data = self.api.get_service_by_name(city, service)
        groups = []
        if region_data and service_data:
            temp_api = YasnoOutagesApi(
                region_id=region_data["id"],
                service_id=service_data["id"],
            )
            await temp_api.fetch_outages_data()
            groups = temp_api.get_groups()

        return self.async_show_form(
            step_id="group",
            data_schema=build_group_schema(groups, None),
        )
