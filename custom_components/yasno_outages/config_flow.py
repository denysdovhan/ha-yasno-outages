"""Config flow for Yasno Outages integration."""

from __future__ import annotations

import datetime
import logging
from typing import Any, Final

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)
from homeassistant.util import dt as dt_utils

from .api import (
    AccountApi,
    YasnoAccount,
    YasnoApi,
    YasnoAuthApi,
    YasnoAuthBlockedError,
    YasnoAuthError,
)
from .api.const import AUTH_MESSAGE_TYPE_SMS, AUTH_MESSAGE_TYPE_VIBER
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_ADDRESS_NAME,
    CONF_FILTER_PROBABLE,
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_LOGIN_MODE,
    CONF_MESSAGE_TYPE,
    CONF_PHONE_NUMBER,
    CONF_PROVIDER,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    CONF_STATUS_ALL_DAY_EVENTS,
    CONF_STEP_HOUSE,
    CONF_STEP_HOUSE_QUERY,
    CONF_STEP_STREET,
    CONF_STEP_STREET_QUERY,
    CONF_STREET_ID,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
    LOGIN_MODE_ACCOUNT,
    LOGIN_MODE_PUBLIC,
    YASNO_GROUP_URL,
)

LOGGER = logging.getLogger(__name__)

SETUP_MODE_GROUP = "group"
SETUP_MODE_ADDRESS = "address"

# Transient form field for the OTP code step; not persisted to the entry.
CONF_OTP_CODE: Final = "otp_code"


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


def build_select_options(options: dict[str, str]) -> list[SelectOptionDict]:
    """Build select options from a value map."""
    return [
        SelectOptionDict(
            label=value,
            value=key,
        )
        for key, value in options.items()
    ]


def build_lookup_options(items: list[dict[str, Any]]) -> dict[str, str]:
    """Build selector options map from API lookup items."""
    return {str(item["id"]): item["value"] for item in items}


def build_street_query_schema() -> vol.Schema:
    """Build the schema for street search query."""
    return vol.Schema({vol.Required(CONF_STEP_STREET_QUERY): str})


def build_street_schema(options: dict[str, str]) -> vol.Schema:
    """Build the schema for street selection."""
    return vol.Schema(
        {
            vol.Required(CONF_STEP_STREET): SelectSelector(
                SelectSelectorConfig(options=build_select_options(options)),
            ),
        }
    )


def build_house_query_schema() -> vol.Schema:
    """Build the schema for house search query."""
    return vol.Schema({vol.Required(CONF_STEP_HOUSE_QUERY): str})


def build_house_schema(options: dict[str, str]) -> vol.Schema:
    """Build the schema for house selection."""
    return vol.Schema(
        {
            vol.Required(CONF_STEP_HOUSE): SelectSelector(
                SelectSelectorConfig(options=build_select_options(options)),
            ),
        }
    )


def build_preferences_schema(
    config_entry: ConfigEntry | None,
) -> vol.Schema:
    """Build the schema for preferences."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=get_config_value(
                    config_entry,
                    CONF_SCAN_INTERVAL,
                    default=15,
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=60,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
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


def build_login_mode_schema(config_entry: ConfigEntry | None) -> vol.Schema:
    """Build the schema for choosing between public-only and account login."""
    return vol.Schema(
        {
            vol.Required(
                CONF_LOGIN_MODE,
                default=get_config_value(
                    config_entry, CONF_LOGIN_MODE, LOGIN_MODE_PUBLIC
                ),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[LOGIN_MODE_PUBLIC, LOGIN_MODE_ACCOUNT],
                    translation_key="login_mode",
                ),
            ),
        },
    )


def build_phone_schema() -> vol.Schema:
    """Build the schema for the phone number + OTP delivery method step."""
    return vol.Schema(
        {
            vol.Required(CONF_PHONE_NUMBER): str,
            vol.Required(
                CONF_MESSAGE_TYPE,
                default=AUTH_MESSAGE_TYPE_SMS,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[AUTH_MESSAGE_TYPE_SMS, AUTH_MESSAGE_TYPE_VIBER],
                    translation_key="message_type",
                ),
            ),
        },
    )


def build_otp_schema() -> vol.Schema:
    """Build the schema for entering the received OTP code."""
    return vol.Schema({vol.Required(CONF_OTP_CODE): str})


def build_account_schema(accounts: list[YasnoAccount]) -> vol.Schema:
    """Build the schema for picking an account when multiple are linked."""
    options = [
        SelectOptionDict(
            value=str(account.id),
            label=f"{account.account_name} ({account.address})",
        )
        for account in accounts
    ]
    return vol.Schema(
        {
            vol.Required(CONF_ACCOUNT_ID): SelectSelector(
                SelectSelectorConfig(options=options),
            ),
        },
    )


class YasnoAccountLoginMixin:
    """
    Shared phone/OTP account-login steps for the config and options flows.

    Requires the including class to provide `self.hass`, `self.data`,
    `self.api` (a `YasnoApi` instance), and an `_async_finish_account_login()`
    coroutine that persists `self.data` (creating or updating the entry).
    """

    async def async_step_phone(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle phone number entry and trigger an SMS/Viber OTP."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._auth_api = YasnoAuthApi()
            try:
                await self._auth_api.start_login(
                    user_input[CONF_PHONE_NUMBER],
                    user_input[CONF_MESSAGE_TYPE],
                )
            except YasnoAuthBlockedError:
                LOGGER.exception("Yasno login blocked by upstream WAF")
                errors["base"] = "login_blocked"
                await self._auth_api.close()
            except (YasnoAuthError, aiohttp.ClientError):
                LOGGER.exception("Failed to start Yasno account login")
                errors["base"] = "login_failed"
                await self._auth_api.close()
            else:
                self.data.update(user_input)
                return await self.async_step_otp()

        return self.async_show_form(
            step_id="phone",
            data_schema=build_phone_schema(),
            errors=errors,
        )

    async def async_step_otp(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle OTP code verification and finish the token exchange."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._auth_api.verify_code(user_input[CONF_OTP_CODE])
                tokens = await self._auth_api.complete_login()
            except YasnoAuthBlockedError:
                LOGGER.exception("Yasno OTP verification blocked by upstream WAF")
                errors["base"] = "login_blocked"
            except (YasnoAuthError, aiohttp.ClientError):
                LOGGER.exception("Failed to verify Yasno OTP code")
                errors["base"] = "invalid_code"
            else:
                self.data[CONF_ACCESS_TOKEN] = tokens.access_token
                self.data[CONF_REFRESH_TOKEN] = tokens.refresh_token
                expires_at = dt_utils.utcnow() + datetime.timedelta(
                    seconds=tokens.expires_in,
                )
                self.data[CONF_TOKEN_EXPIRES_AT] = expires_at.isoformat()
                return await self._async_load_accounts()
            finally:
                await self._auth_api.close()

        return self.async_show_form(
            step_id="otp",
            data_schema=build_otp_schema(),
            errors=errors,
        )

    async def _async_load_accounts(self) -> ConfigFlowResult:
        """Fetch linked accounts/addresses and continue the flow."""
        account_api = AccountApi(self.data[CONF_ACCESS_TOKEN])
        self._accounts = await account_api.fetch_accounts()
        self._addresses = await account_api.fetch_addresses()

        if not self._accounts:
            return self.async_show_form(
                step_id="otp",
                data_schema=build_otp_schema(),
                errors={"base": "no_accounts"},
            )

        if len(self._accounts) == 1:
            return await self._async_finish_with_account(self._accounts[0])
        return await self.async_step_account()

    async def async_step_account(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle account selection when multiple accounts are linked."""
        if user_input is not None:
            account_id = int(user_input[CONF_ACCOUNT_ID])
            account = next(
                (a for a in self._accounts if a.id == account_id),
                self._accounts[0],
            )
            return await self._async_finish_with_account(account)

        return self.async_show_form(
            step_id="account",
            data_schema=build_account_schema(self._accounts),
        )

    async def _async_finish_with_account(
        self,
        account: YasnoAccount,
    ) -> ConfigFlowResult:
        """Resolve region/provider/group from the account's address and finish."""
        address = next(
            (a for a in self._addresses if a.name == account.address),
            self._addresses[0] if self._addresses else None,
        )
        if address is None:
            return self.async_show_form(
                step_id="otp",
                data_schema=build_otp_schema(),
                errors={"base": "no_address"},
            )

        if not self.api.regions_data:
            await self.api.fetch_regions()

        region_data = next(
            (r for r in self.api.get_regions() if r["id"] == address.region_id),
            None,
        )
        provider_data = None
        if region_data:
            provider_data = next(
                (p for p in region_data.get("dsos", []) if p["id"] == address.dso_id),
                None,
            )

        self.data[CONF_ACCOUNT_ID] = account.id
        self.data[CONF_REGION] = region_data["value"] if region_data else ""
        self.data[CONF_PROVIDER] = (
            provider_data["name"] if provider_data else address.dso_name
        )
        self.data[CONF_GROUP] = f"{address.group}.{address.subgroup}"
        self.data[CONF_LOGIN_MODE] = LOGIN_MODE_ACCOUNT
        self.data.setdefault(CONF_FILTER_PROBABLE, True)
        self.data.setdefault(CONF_STATUS_ALL_DAY_EVENTS, True)

        return await self._async_finish_account_login()


class YasnoOutagesOptionsFlow(OptionsFlow):
    """Handle options flow for Yasno Outages."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self.api = YasnoApi()
        self.data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle options."""
        if user_input is not None:
            LOGGER.debug("Updating options: %s", user_input)
            self.data.update(user_input)
            return self.async_create_entry(title="", data=self.data)

        return self.async_show_form(
            step_id="init",
            data_schema=build_preferences_schema(self.config_entry),
        )


class YasnoOutagesConfigFlow(YasnoAccountLoginMixin, ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yasno Outages."""

    VERSION = 3
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize config flow."""
        self.api = YasnoApi()
        self.data: dict[str, Any] = {}
        self._street_options: dict[str, str] = {}
        self._house_options: dict[str, str] = {}
        self._street_name = ""
        self._house_name = ""
        self._is_reconfigure = False
        self._auth_api: YasnoAuthApi | None = None
        self._accounts: list[YasnoAccount] = []
        self._addresses: list = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> YasnoOutagesOptionsFlow:  # noqa: ARG004
        """Get the options flow for this handler."""
        return YasnoOutagesOptionsFlow()

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

    def _active_config_entry(self) -> ConfigEntry | None:
        """Return config entry for reconfigure source."""
        if self._is_reconfigure:
            return self._get_reconfigure_entry()
        return None

    def _build_entry_data(self) -> dict[str, Any]:
        """Build config-entry data from current flow data."""
        common_data: dict[str, Any] = {
            CONF_REGION: self.data[CONF_REGION],
            CONF_PROVIDER: self.data[CONF_PROVIDER],
            CONF_FILTER_PROBABLE: self.data[CONF_FILTER_PROBABLE],
            CONF_STATUS_ALL_DAY_EVENTS: self.data[CONF_STATUS_ALL_DAY_EVENTS],
        }
        if self.data.get(CONF_GROUP):
            return {**common_data, CONF_GROUP: self.data[CONF_GROUP]}
        return {
            **common_data,
            CONF_STREET_ID: self.data[CONF_STREET_ID],
            CONF_HOUSE_ID: self.data[CONF_HOUSE_ID],
            CONF_ADDRESS_NAME: f"{self._street_name} {self._house_name}",
        }

    def _build_entry_title(self) -> str:
        """Build config-entry title from current flow data."""
        if self.data.get(CONF_GROUP):
            return build_entry_title(
                region=self.data[CONF_REGION],
                provider=self.data[CONF_PROVIDER],
                group=self.data[CONF_GROUP],
            )
        return build_address_entry_title(
            region=self.data[CONF_REGION],
            street=self._street_name,
            house=self._house_name,
        )

    def _build_reconfigure_options(self, config_entry: ConfigEntry) -> dict[str, Any]:
        """Build options map preserving existing preferences."""
        options = dict(config_entry.options)
        scan_interval = self.data.get(
            CONF_SCAN_INTERVAL,
            get_config_value(config_entry, CONF_SCAN_INTERVAL, default=15),
        )
        options.update(
            {
                CONF_SCAN_INTERVAL: scan_interval,
                CONF_FILTER_PROBABLE: self.data[CONF_FILTER_PROBABLE],
                CONF_STATUS_ALL_DAY_EVENTS: self.data[CONF_STATUS_ALL_DAY_EVENTS],
            }
        )
        return options

    async def async_step_reconfigure(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}
        self._is_reconfigure = True
        config_entry = self._active_config_entry()
        if config_entry is None:
            return self.async_abort(reason="unknown")

        if not self.data:
            self.data = dict(config_entry.data)
            self.data.update(config_entry.options)

        # Account-mode entries are reconfigured by re-authenticating,
        # not by re-selecting region/provider/group/address.
        if get_config_value(config_entry, CONF_LOGIN_MODE) == LOGIN_MODE_ACCOUNT:
            return await self.async_step_phone()

        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_provider()

        try:
            await self.api.fetch_regions()
        except Exception:  # noqa: BLE001
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=build_region_schema(api=self.api, config_entry=config_entry),
            errors=errors,
        )

    async def _async_finish_account_login(self) -> ConfigFlowResult:
        """Create or update the config entry from account-mode data."""
        self.data.setdefault(CONF_FILTER_PROBABLE, True)
        self.data.setdefault(CONF_STATUS_ALL_DAY_EVENTS, True)
        title = build_entry_title(
            region=self.data[CONF_REGION],
            provider=self.data[CONF_PROVIDER],
            group=self.data[CONF_GROUP],
        )
        if self.source == SOURCE_RECONFIGURE:
            config_entry = self._active_config_entry()
            if config_entry is None:
                return self.async_abort(reason="unknown")
            return self.async_update_reload_and_abort(
                config_entry,
                title=title,
                data=self.data,
                options=self._build_reconfigure_options(config_entry),
            )
        return self.async_create_entry(title=title, data=self.data)

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step: choose public-only or account login."""
        if user_input is not None:
            LOGGER.debug("Login mode selected: %s", user_input)
            self.data.update(user_input)
            if self.data[CONF_LOGIN_MODE] == LOGIN_MODE_ACCOUNT:
                return await self.async_step_phone()
            return await self.async_step_region()

        return self.async_show_form(
            step_id="user",
            data_schema=build_login_mode_schema(None),
        )

    async def async_step_region(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the region selection step."""
        if user_input is not None:
            LOGGER.debug("Region selected: %s", user_input)
            self.data.update(user_input)
            return await self.async_step_provider()

        await self.api.fetch_regions()

        return self.async_show_form(
            step_id="region",
            data_schema=build_region_schema(
                api=self.api,
                config_entry=self._active_config_entry(),
            ),
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
                config_entry=self._active_config_entry(),
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
            menu_options=[SETUP_MODE_ADDRESS, SETUP_MODE_GROUP],
        )

    async def async_step_address(
        self,
        user_input: dict | None = None,  # noqa: ARG002
    ) -> ConfigFlowResult:
        """Handle address setup method."""
        self.data.pop(CONF_GROUP, None)
        return await self.async_step_street_query()

    async def async_step_street_query(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle street search query."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = user_input[CONF_STEP_STREET_QUERY].strip()
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
                        if len(streets) == 1:
                            street = streets[0]
                            self.data[CONF_STREET_ID] = street["id"]
                            self._street_name = street["value"]
                            return await self.async_step_house_query()
                        self._street_options = build_lookup_options(streets)
                        return await self.async_step_street()

        return self.async_show_form(
            step_id="street_query",
            data_schema=build_street_query_schema(),
            errors=errors,
        )

    async def async_step_street(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle street selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            street_id = user_input[CONF_STEP_STREET]
            street_name = self._street_options.get(street_id)
            if not street_name:
                errors["base"] = "no_streets"
            else:
                self.data[CONF_STREET_ID] = int(street_id)
                self._street_name = street_name
                return await self.async_step_house_query()

        return self.async_show_form(
            step_id="street",
            data_schema=build_street_schema(self._street_options),
            errors=errors,
        )

    async def async_step_house(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle house selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            house_id = user_input[CONF_STEP_HOUSE]
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
            data_schema=build_house_schema(self._house_options),
            errors=errors,
        )

    async def async_step_house_query(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle house search query."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = user_input[CONF_STEP_HOUSE_QUERY].strip()
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
                        self._house_options = build_lookup_options(houses)
                        return await self.async_step_house()

        return self.async_show_form(
            step_id="house_query",
            data_schema=build_house_query_schema(),
            errors=errors,
        )

    async def async_step_preferences(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle preferences before entry creation."""
        if user_input is not None:
            self.data.update(user_input)
            data = self._build_entry_data()
            title = self._build_entry_title()
            if self.source == SOURCE_RECONFIGURE:
                config_entry = self._active_config_entry()
                if config_entry is None:
                    return self.async_abort(reason="unknown")
                return self.async_update_reload_and_abort(
                    config_entry,
                    title=title,
                    data=data,
                    options=self._build_reconfigure_options(config_entry),
                )
            return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="preferences",
            data_schema=build_preferences_schema(self._active_config_entry()),
        )

    async def async_step_group(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle the group step."""
        self.data.update(
            {
                CONF_STREET_ID: None,
                CONF_HOUSE_ID: None,
                CONF_ADDRESS_NAME: None,
            }
        )
        if user_input is not None:
            LOGGER.debug("User input: %s", user_input)
            self.data.update(user_input)
            self.data[CONF_LOGIN_MODE] = LOGIN_MODE_PUBLIC
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
            data_schema=build_group_schema(groups, self._active_config_entry()),
            description_placeholders={"yasno_group_url": YASNO_GROUP_URL},
        )
