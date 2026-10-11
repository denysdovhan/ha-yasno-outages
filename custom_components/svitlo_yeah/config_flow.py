"""Config flow for Svitlo Yeah integration."""

import logging
from typing import TYPE_CHECKING, Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.translation import async_get_translations

from .api.alerts_energy import AlertsEnergyClient
from .api.dtek.base import FetchResult
from .api.dtek.json import DtekAPIJson
from .api.yasno import YASNO_REGIONS_ENDPOINT, YasnoApi
from .const import (
    ALERTS_ENERGY_URL,
    CONF_GROUP,
    CONF_PROVIDER,
    CONF_PROVIDER_TYPE,
    CONF_REGION,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    DTEK_PROVIDER_URLS,
    NAME,
    PROVIDER_TYPE_ALERTS_ENERGY,
    PROVIDER_TYPE_DTEK_JSON,
    PROVIDER_TYPE_YASNO,
    TZ_UA,
    common_translation_key,
)
from .models.providers import (
    AlertsEnergyProvider,
    BaseProvider,
    DTEKJsonProvider,
    YasnoProvider,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

LOGGER = logging.getLogger(__name__)

# The checkbox of the form that accepts outdated DTEK data
CONF_ACKNOWLEDGE = "acknowledge"


class IntegrationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Svitlo Yeah."""

    # Each change of the entry data shape needs a new VERSION and async_migrate_entry
    VERSION = CONFIG_ENTRY_VERSION
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self.available_providers: dict[str, BaseProvider] = {}
        self.data: dict[str, Any] = {}
        # Whether the user accepted the outdated DTEK data in this flow
        self._stale_ack = False
        # The update time of the outdated DTEK data, which the warning shows
        self._stale_updated = ""

    @override
    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step: select provider."""
        if user_input is not None:
            LOGGER.debug("async_step_user: User input: %s", user_input)
            # The select of the form accepts only the keys of available_providers
            selected_provider = self.available_providers[user_input[CONF_PROVIDER]]

            self.data[CONF_PROVIDER_TYPE] = selected_provider.provider_type
            self.data[CONF_PROVIDER] = selected_provider.provider_id
            if selected_provider.provider_type == PROVIDER_TYPE_YASNO:
                self.data[CONF_REGION] = selected_provider.region_id
            elif selected_provider.provider_type == PROVIDER_TYPE_ALERTS_ENERGY:
                return await self.async_step_alerts_energy_group()

            # noinspection PyTypeChecker
            return await self.async_step_group()

        LOGGER.debug("async_step_user: No User input yet")
        api_yasno = YasnoApi(self.hass)
        await api_yasno.fetch_yasno_regions()
        yasno_regions = api_yasno.regions or []
        LOGGER.debug("async_step_user: yasno_regions: %s", yasno_regions)
        yasno_providers: list[YasnoProvider] = []
        if yasno_regions:
            for region in yasno_regions:
                yasno_providers.extend(region.dsos)
        else:
            LOGGER.debug(
                "Failed to fetch Yasno regions. Check internet or report issue"
            )
            # Continue with DTEK only

        # Create DTEKJsonProvider instances for each available provider key
        dtek_providers = [DTEKJsonProvider(region_name=_) for _ in DTEK_PROVIDER_URLS]

        alerts_energy_provider = AlertsEnergyProvider()

        all_providers = yasno_providers + dtek_providers + [alerts_energy_provider]
        self.available_providers = {_.unique_key: _ for _ in all_providers}

        provider_options = [
            SelectOptionDict(
                label=_.translation_key,
                value=_.unique_key,
            )
            for _ in self.available_providers.values()
        ]

        data_schema = vol.Schema(
            {
                # default=None keeps the frontend from picking a provider for the user
                vol.Required(CONF_PROVIDER, default=None): SelectSelector(
                    SelectSelectorConfig(
                        options=provider_options,
                        translation_key="provider",
                        mode=SelectSelectorMode.DROPDOWN,
                        sort=False,
                    ),
                ),
            },
        )

        # noinspection PyTypeChecker
        return self.async_show_form(step_id="user", data_schema=data_schema)

    async def _async_entry_title(self, data: Mapping[str, Any]) -> str:
        """
        Return the device name in the language of the server, as the entry title.

        Thus the entries differ on the page of the integration.
        """
        names = await async_get_translations(
            self.hass, self.hass.config.language, "common", [DOMAIN]
        )
        provider_type = data.get(CONF_PROVIDER_TYPE)
        provider_id = data.get(CONF_PROVIDER)
        provider_name = names.get(
            common_translation_key(str(provider_id)), str(provider_id)
        )
        if provider_type == PROVIDER_TYPE_ALERTS_ENERGY:
            group = data.get(CONF_GROUP, "")
            return f"{provider_name} Alerts Energy {group}".strip()
        if provider_type == PROVIDER_TYPE_YASNO:
            api = YasnoApi(self.hass)
            # The regions come from the class cache, if a flow or an entry got them
            await api.fetch_yasno_regions()
            region_id = data.get(CONF_REGION)
            region = api.get_region_by_id(region_id) if region_id else None
            dsos = region.dsos if region else []
            provider = next((_ for _ in dsos if _.provider_id == provider_id), None)
            if region is None or provider is None:
                # Without the Yasno regions the title has no names to show
                return NAME
            provider_name = f"{region.name} {provider.short_name}"
        return f"{provider_name} {data.get(CONF_GROUP)}"

    async def _async_save_group(self, user_input: dict) -> ConfigFlowResult:
        """Create the entry with the chosen group, or give the group to the entry."""
        LOGGER.debug("async_step_group: User input: %s", user_input)
        self.data.update(user_input)  # add group to the config

        if self.source == SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            if self.data[CONF_GROUP] == entry.data.get(CONF_GROUP):
                # noinspection PyTypeChecker
                return self.async_abort(reason="reconfigure_unchanged")

        # One entry for each provider and group: a second one only repeats it
        self._async_abort_entries_match(
            {
                key: self.data[key]
                for key in (
                    CONF_PROVIDER_TYPE,
                    CONF_REGION,
                    CONF_PROVIDER,
                    CONF_GROUP,
                )
                if key in self.data
            }
        )

        if self.source == SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            # A title of the user stays, a title of the integration follows the group
            title = entry.title
            if title in (NAME, await self._async_entry_title(entry.data)):
                title = await self._async_entry_title(self.data)
            # The update listener reloads it, and the reason keeps the integration text
            # noinspection PyTypeChecker
            return self.async_update_and_abort(
                entry,
                title=title,
                data_updates={CONF_GROUP: self.data[CONF_GROUP]},
                reason="reconfigure_successful",
            )

        LOGGER.debug("async_step_group: Done. Creating entry from %s", self.data)
        # noinspection PyTypeChecker
        return self.async_create_entry(
            title=await self._async_entry_title(self.data), data=self.data
        )

    async def async_step_group(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: select group."""
        if user_input is not None:
            return await self._async_save_group(user_input)

        LOGGER.debug("async_step_user: No User input yet")

        region_id = self.data.get(CONF_REGION)
        provider_id = self.data[CONF_PROVIDER]
        provider_type = self.data[CONF_PROVIDER_TYPE]

        groups = []
        group_labels: dict[str, str] = {}
        if provider_type == PROVIDER_TYPE_YASNO:
            if region_id and provider_id:
                temp_api = YasnoApi(
                    self.hass,
                    region_id=region_id,
                    provider_id=provider_id,
                )
                await temp_api.fetch_planned_outage_data()
                groups = temp_api.get_yasno_groups()
                if not groups:
                    # noinspection PyTypeChecker
                    return self.async_abort(
                        reason="yasno_connection_error",
                        description_placeholders={"url": YASNO_REGIONS_ENDPOINT},
                    )

        elif provider_type == PROVIDER_TYPE_DTEK_JSON and provider_id:
            urls = DTEK_PROVIDER_URLS.get(provider_id, [])
            if urls:
                temp_api = DtekAPIJson(self.hass, urls=urls, group=None)
                result = await temp_api.fetch_data(allow_stale_data=True)
                groups = temp_api.get_dtek_region_groups()
                if result is FetchResult.UNAVAILABLE or not groups:
                    # noinspection PyTypeChecker
                    return self.async_abort(
                        reason=(
                            "dtek_json_unavailable"
                            if result is FetchResult.UNAVAILABLE
                            else "dtek_json_empty_data"
                        ),
                        # One source on each line of the text
                        description_placeholders={"urls": "\n".join(urls)},
                    )
                if result is FetchResult.STALE and not self._stale_ack:
                    # The source gives the update time in Kyiv, so the warning does too
                    updated = temp_api.get_updated_on()
                    self._stale_updated = (
                        updated.astimezone(TZ_UA).strftime("%d.%m.%Y %H:%M")
                        if updated
                        else ""
                    )
                    # noinspection PyTypeChecker
                    return await self.async_step_stale_confirm()
                group_labels = temp_api.get_dtek_region_group_labels()

        # A select takes plain values or labeled options, not a mix of both
        group_options: list[str] | list[SelectOptionDict] = groups
        if group_labels:
            group_options = [
                SelectOptionDict(value=group, label=group_labels.get(group, group))
                for group in groups
            ]

        # On reconfigure, preselect the current group while the source lists it
        current_group = self.data.get(CONF_GROUP)
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_GROUP,
                    default=current_group if current_group in groups else None,
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=group_options,
                        translation_key="group",
                    ),
                ),
            },
        )

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id="group",
            data_schema=data_schema,
            description_placeholders={
                "yasno_url": "https://static.yasno.ua/kyiv/outages",
                "dtek_url": "https://www.dtek-krem.com.ua/ua/shutdowns",
            },
        )

    async def async_step_reconfigure(
        self,
        user_input: dict | None = None,  # noqa: ARG002  # the flow manager passes it
    ) -> ConfigFlowResult:
        """Let the user pick another group for an existing entry."""
        entry = self._get_reconfigure_entry()
        self.data = dict(entry.data)
        if self.data.get(CONF_PROVIDER_TYPE) == PROVIDER_TYPE_ALERTS_ENERGY:
            return await self.async_step_alerts_energy_group()
        # noinspection PyTypeChecker
        return await self.async_step_group()

    async def async_step_stale_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Warn about stale DTEK JSON data and require acknowledgement."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_ACKNOWLEDGE):
                self._stale_ack = True
                # noinspection PyTypeChecker
                return await self.async_step_group()
            errors[CONF_ACKNOWLEDGE] = "acknowledge_required"

        data_schema = vol.Schema(
            {vol.Required(CONF_ACKNOWLEDGE, default=False): bool},
        )

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id="stale_confirm",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"updated": self._stale_updated},
        )

    async def async_step_alerts_energy_group(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Select a Sumy subgroup from the published source registry."""
        if user_input is not None:
            return await self._async_save_group(user_input)

        client = AlertsEnergyClient(self.hass)
        if not await client.fetch_data() or not (groups := client.get_groups()):
            return self.async_abort(
                reason="alerts_energy_connection_error",
                description_placeholders={"url": ALERTS_ENERGY_URL},
            )
        current_group = self.data.get(CONF_GROUP)
        return self.async_show_form(
            step_id="alerts_energy_group",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_GROUP,
                        default=current_group if current_group in groups else None,
                    ): SelectSelector(SelectSelectorConfig(options=groups)),
                }
            ),
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],  # noqa: ARG002  # obsolete HA requests
    ) -> ConfigFlowResult:
        """Close an obsolete login request after the Sumy migration."""
        return self.async_abort(reason="reauth_not_required")
