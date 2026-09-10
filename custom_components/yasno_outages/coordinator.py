"""Data coordinator for Yasno Outages integration."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_SCAN_INTERVAL, STATE_UNKNOWN
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_utils

from .api import (
    AccountApi,
    OutageEvent,
    OutageEventType,
    YasnoApi,
    YasnoApiError,
    YasnoAuthApi,
)
from .api.const import (
    API_STATUS_EMERGENCY_SHUTDOWNS,
    API_STATUS_NO_OUTAGES,
    API_STATUS_SCHEDULE_APPLIES,
    API_STATUS_WAITING_FOR_SCHEDULE,
    TARIFF_ZONE_DAY,
    TARIFF_ZONE_NIGHT,
)
from .api.models import (
    OutageSource,
    YasnoAccount,
    YasnoAccountDebt,
    YasnoContract,
    YasnoTariff,
)
from .const import (
    AUTH_TOKEN_REFRESH_MARGIN,
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_ID,
    CONF_ADDRESS_NAME,
    CONF_FILTER_PROBABLE,
    CONF_GROUP,
    CONF_LOGIN_MODE,
    CONF_PROVIDER,
    CONF_REFRESH_TOKEN,
    CONF_REGION,
    CONF_STATUS_ALL_DAY_EVENTS,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
    LOGIN_MODE_ACCOUNT,
    PLANNED_OUTAGE_LOOKAHEAD,
    PLANNED_OUTAGE_TEXT_FALLBACK,
    PROBABLE_OUTAGE_LOOKAHEAD,
    PROBABLE_OUTAGE_TEXT_FALLBACK,
    PROVIDER_DTEK_FULL,
    PROVIDER_DTEK_SHORT,
    STATE_NORMAL,
    STATE_OUTAGE,
    STATE_STATUS_EMERGENCY_SHUTDOWNS,
    STATE_STATUS_NO_OUTAGES,
    STATE_STATUS_SCHEDULE_APPLIES,
    STATE_STATUS_WAITING_FOR_SCHEDULE,
    STATUS_EMERGENCY_SHUTDOWNS_TEXT_FALLBACK,
    STATUS_NO_OUTAGES_TEXT_FALLBACK,
    STATUS_SCHEDULE_APPLIES_TEXT_FALLBACK,
    STATUS_WAITING_FOR_SCHEDULE_TEXT_FALLBACK,
    TARIFF_PLAN_NAME_TEXT_FALLBACKS,
    TARIFF_PLAN_NAME_TRANSLATION_KEYS,
    TRANSLATION_KEY_EVENT_PLANNED_OUTAGE,
    TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE,
    TRANSLATION_KEY_STATUS_EMERGENCY_SHUTDOWNS,
    TRANSLATION_KEY_STATUS_NO_OUTAGES,
    TRANSLATION_KEY_STATUS_SCHEDULE_APPLIES,
    TRANSLATION_KEY_STATUS_WAITING_FOR_SCHEDULE,
)
from .helpers import merge_consecutive_outages

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api.base import BaseYasnoApi

LOGGER = logging.getLogger(__name__)

EVENT_TYPE_STATE_MAP: dict[OutageEventType, str] = {
    OutageEventType.DEFINITE: STATE_OUTAGE,
    OutageEventType.NOT_PLANNED: STATE_NORMAL,
}

STATUS_STATE_MAP: dict[str, str] = {
    API_STATUS_NO_OUTAGES: STATE_STATUS_NO_OUTAGES,
    API_STATUS_SCHEDULE_APPLIES: STATE_STATUS_SCHEDULE_APPLIES,
    API_STATUS_WAITING_FOR_SCHEDULE: STATE_STATUS_WAITING_FOR_SCHEDULE,
    API_STATUS_EMERGENCY_SHUTDOWNS: STATE_STATUS_EMERGENCY_SHUTDOWNS,
}


def is_outage_event(event: OutageEvent | None) -> bool:
    """Return True for outage events that should create calendar entries."""
    LOGGER.debug("Checking if event is an outage: %s", event)
    return bool(event and event.event_type != OutageEventType.NOT_PLANNED)


def find_next_outage(
    events: list[OutageEvent],
    now: datetime.datetime,
) -> OutageEvent | None:
    """Find the next outage event that starts after the given time."""
    for event in events:
        if event.start > now:
            return event
    return None


def simplify_provider_name(provider_name: str) -> str:
    """Simplify provider names for cleaner display in device names."""
    # Replace long DTEK provider names with just "ДТЕК"
    if PROVIDER_DTEK_FULL in provider_name.upper():
        return PROVIDER_DTEK_SHORT

    # Add more provider simplifications here as needed
    return provider_name


class YasnoOutagesCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Yasno outages data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: YasnoApi,
        group: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=datetime.timedelta(
                minutes=config_entry.options.get(
                    CONF_SCAN_INTERVAL,
                    config_entry.data.get(CONF_SCAN_INTERVAL, 15),
                ),
            ),
        )
        self.hass = hass
        self.config_entry = config_entry
        self.translations = {}

        # Get configuration values
        self.region = config_entry.options.get(
            CONF_REGION,
            config_entry.data.get(CONF_REGION),
        )
        self.provider = config_entry.options.get(
            CONF_PROVIDER,
            config_entry.data.get(CONF_PROVIDER),
        )
        self.group = group or config_entry.options.get(
            CONF_GROUP, config_entry.data.get(CONF_GROUP)
        )
        self.address_name = config_entry.data.get(CONF_ADDRESS_NAME)
        self.filter_probable = config_entry.options.get(
            CONF_FILTER_PROBABLE,
            config_entry.data.get(CONF_FILTER_PROBABLE, True),
        )
        self.status_all_day_events = config_entry.options.get(
            CONF_STATUS_ALL_DAY_EVENTS,
            config_entry.data.get(CONF_STATUS_ALL_DAY_EVENTS, True),
        )

        if not self.region:
            region_required_msg = (
                "Region not set in configuration - this should not happen "
                "with proper config flow"
            )
            region_error = "Region configuration is required"
            LOGGER.error(region_required_msg)
            raise ValueError(region_error)

        if not self.provider:
            provider_required_msg = (
                "Provider not set in configuration - this should not happen "
                "with proper config flow"
            )
            provider_error = "Provider configuration is required"
            LOGGER.error(provider_required_msg)
            raise ValueError(provider_error)

        if not self.group:
            group_required_msg = (
                "Group not set in configuration - this should not happen "
                "with proper config flow"
            )
            group_error = "Group configuration is required"
            LOGGER.error(group_required_msg)
            raise ValueError(group_error)

        self._provider_name = ""  # Cache the provider name

        # Use the provided API instance
        self.api = api

        # Account login mode (optional authenticated account data)
        self.login_mode = config_entry.options.get(
            CONF_LOGIN_MODE,
            config_entry.data.get(CONF_LOGIN_MODE),
        )
        self.account_id = config_entry.options.get(
            CONF_ACCOUNT_ID,
            config_entry.data.get(CONF_ACCOUNT_ID),
        )
        self._account: YasnoAccount | None = None
        self._contract: YasnoContract | None = None
        self._debt: YasnoAccountDebt | None = None
        self._tariff: YasnoTariff | None = None

    async def _async_update_data(self) -> None:
        """Fetch data from new Yasno API."""
        await self.async_fetch_translations()

        # Cache current data before fetching (for fallback on API failure)
        planned_cache = self.api.planned.planned_outages_data
        probable_cache = self.api.probable.probable_outages_data

        # Fetch planned outages data
        try:
            await self.api.planned.fetch_data()
        except YasnoApiError:
            LOGGER.warning(
                "Failed to fetch planned outages, using cached data", exc_info=True
            )
            self.api.planned.planned_outages_data = planned_cache

        # Fetch probable outages data
        try:
            await self.api.probable.fetch_data()
        except YasnoApiError:
            LOGGER.warning(
                "Failed to fetch probable outages, using cached data", exc_info=True
            )
            self.api.probable.probable_outages_data = probable_cache

        # Fetch authenticated account data (balance/debt/meter readings)
        if self.login_mode == LOGIN_MODE_ACCOUNT:
            try:
                await self._async_update_account_data()
            except Exception:  # noqa: BLE001
                LOGGER.warning("Failed to fetch Yasno account data", exc_info=True)

    async def _async_ensure_valid_token(self) -> str | None:
        """Refresh the access token if it is close to expiry, persisting it."""
        access_token = self.config_entry.data.get(CONF_ACCESS_TOKEN)
        refresh_token = self.config_entry.data.get(CONF_REFRESH_TOKEN)
        expires_at_raw = self.config_entry.data.get(CONF_TOKEN_EXPIRES_AT)
        if not access_token or not refresh_token:
            return None

        expires_at = (
            datetime.datetime.fromisoformat(expires_at_raw) if expires_at_raw else None
        )
        margin = datetime.timedelta(minutes=AUTH_TOKEN_REFRESH_MARGIN)
        if expires_at and dt_utils.utcnow() < expires_at - margin:
            return access_token

        auth_api = YasnoAuthApi()
        try:
            tokens = await auth_api.refresh(refresh_token)
        except Exception:  # noqa: BLE001
            LOGGER.warning("Failed to refresh Yasno account token", exc_info=True)
            return access_token
        finally:
            await auth_api.close()

        new_expires_at = dt_utils.utcnow() + datetime.timedelta(
            seconds=tokens.expires_in,
        )
        new_data = dict(self.config_entry.data)
        new_data[CONF_ACCESS_TOKEN] = tokens.access_token
        new_data[CONF_REFRESH_TOKEN] = tokens.refresh_token
        new_data[CONF_TOKEN_EXPIRES_AT] = new_expires_at.isoformat()
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=new_data,
        )
        return tokens.access_token

    async def _async_update_account_data(self) -> None:
        """Fetch account/contract/debt data for the logged-in Yasno account."""
        access_token = await self._async_ensure_valid_token()
        if not access_token:
            return

        account_api = AccountApi(access_token)
        accounts = await account_api.fetch_accounts()
        contracts = await account_api.fetch_contracts()

        account = None
        if self.account_id is not None:
            account = next((a for a in accounts if a.id == self.account_id), None)
        if account is None and accounts:
            account = accounts[0]
        self._account = account

        contract = None
        if account:
            contract = next(
                (c for c in contracts if c.id == account.id),
                contracts[0] if contracts else None,
            )
        self._contract = contract

        if account:
            debts = await account_api.fetch_debt([account.id])
            self._debt = debts.get(account.id)
            self._tariff = await account_api.fetch_tariff(account.id)
        else:
            self._debt = None
            self._tariff = None

    def _event_to_state(self, event: OutageEvent | None) -> str:
        """Map outage event to electricity state."""
        return (
            EVENT_TYPE_STATE_MAP.get(event.event_type, STATE_UNKNOWN)
            if event
            else STATE_UNKNOWN
        )

    async def async_fetch_translations(self) -> None:
        """Fetch translations."""
        self.translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "common",
            [DOMAIN],
        )

    @property
    def event_summary_map(self) -> dict[OutageSource, str]:
        """Return localized summaries by source with fallbacks."""
        return {
            OutageSource.PLANNED: self.translations.get(
                TRANSLATION_KEY_EVENT_PLANNED_OUTAGE, PLANNED_OUTAGE_TEXT_FALLBACK
            ),
            OutageSource.PROBABLE: self.translations.get(
                TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE, PROBABLE_OUTAGE_TEXT_FALLBACK
            ),
        }

    @property
    def status_event_summary_map(self) -> dict[str, str]:
        """Return localized summaries for planned status events."""
        return {
            STATE_STATUS_NO_OUTAGES: self.translations.get(
                TRANSLATION_KEY_STATUS_NO_OUTAGES,
                STATUS_NO_OUTAGES_TEXT_FALLBACK,
            ),
            STATE_STATUS_SCHEDULE_APPLIES: self.translations.get(
                TRANSLATION_KEY_STATUS_SCHEDULE_APPLIES,
                STATUS_SCHEDULE_APPLIES_TEXT_FALLBACK,
            ),
            STATE_STATUS_WAITING_FOR_SCHEDULE: self.translations.get(
                TRANSLATION_KEY_STATUS_WAITING_FOR_SCHEDULE,
                STATUS_WAITING_FOR_SCHEDULE_TEXT_FALLBACK,
            ),
            STATE_STATUS_EMERGENCY_SHUTDOWNS: self.translations.get(
                TRANSLATION_KEY_STATUS_EMERGENCY_SHUTDOWNS,
                STATUS_EMERGENCY_SHUTDOWNS_TEXT_FALLBACK,
            ),
        }

    @property
    def region_name(self) -> str:
        """Get the configured region name."""
        return self.region or ""

    @property
    def provider_name(self) -> str:
        """Get the configured provider name."""
        # Return cached name if available (but apply simplification first)
        if self._provider_name:
            return simplify_provider_name(self._provider_name)

        # Fallback to lookup if not cached yet
        if not self.api.regions_data:
            return ""

        region_data = self.api.get_region_by_name(self.region)
        if not region_data:
            return ""

        providers = region_data.get("dsos", [])
        for provider in providers:
            if (provider_name := provider.get("name", "")) == self.provider:
                # Cache the simplified name
                self._provider_name = provider_name
                return simplify_provider_name(provider_name)

        return ""

    @property
    def current_event(self) -> OutageEvent | None:
        """Get the current planned event (including NotPlanned events)."""
        try:
            return self.api.planned.get_current_event(dt_utils.now())
        except Exception:  # noqa: BLE001
            LOGGER.warning(
                "Failed to get current event, sensors will show unknown state",
                exc_info=True,
            )
            return None

    @property
    def current_state(self) -> str:
        """Get the current state."""
        if event := self.current_event:
            return self._event_to_state(event)

        # Yasno omits a current slot when the day status is "No Outages".
        if self.status_today == STATE_STATUS_NO_OUTAGES:
            return STATE_NORMAL

        return STATE_UNKNOWN

    @property
    def schedule_updated_on(self) -> datetime.datetime | None:
        """Get the schedule last updated timestamp."""
        return self.api.planned.get_updated_on()

    @property
    def today_date(self) -> datetime.date | None:
        """Get today's date."""
        return self.api.planned.get_today_date()

    @property
    def tomorrow_date(self) -> datetime.date | None:
        """Get tomorrow's date."""
        return self.api.planned.get_tomorrow_date()

    @property
    def status_today(self) -> str | None:
        """Get the status for today."""
        return STATUS_STATE_MAP.get(self.api.planned.get_status_today(), STATE_UNKNOWN)

    @property
    def status_tomorrow(self) -> str | None:
        """Get the status for tomorrow."""
        return STATUS_STATE_MAP.get(
            self.api.planned.get_status_tomorrow(), STATE_UNKNOWN
        )

    @property
    def next_planned_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next planned outage time."""
        now = dt_utils.now()
        events = self.get_merged_outages(
            self.api.planned,
            now,
            PLANNED_OUTAGE_LOOKAHEAD,
        )

        if event := find_next_outage(events, now):
            LOGGER.debug("Next planned outage: %s", event)
            return event.start

        return None

    @property
    def next_probable_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next probable outage time."""
        now = dt_utils.now()
        events = self.get_merged_outages(
            self.api.probable,
            now,
            PROBABLE_OUTAGE_LOOKAHEAD,
        )

        if event := find_next_outage(events, now):
            LOGGER.debug("Next probable outage: %s", event)
            return event.start

        return None

    @property
    def next_connectivity(self) -> datetime.date | datetime.datetime | None:
        """
        Get next connectivity time.

        Only planned events determine connectivity.
        Probable events are forecasts and do not affect connectivity calculation.
        """
        now = dt_utils.now()
        events = self.get_merged_outages(
            self.api.planned,
            now,
            PLANNED_OUTAGE_LOOKAHEAD,
        )

        # Check if we are in an outage
        for event in events:
            if event.start <= now < event.end:
                return event.end

        # Find next outage
        if event := find_next_outage(events, now):
            LOGGER.debug("Next connectivity event: %s", event)
            return event.end

        return None

    @property
    def has_account_data(self) -> bool:
        """Return True if this entry is logged in and account data was fetched."""
        return self.login_mode == LOGIN_MODE_ACCOUNT and self._account is not None

    @property
    def account_number(self) -> str | None:
        """Get the account number of the logged-in Yasno account."""
        return self._account.account_number if self._account else None

    @property
    def account_address(self) -> str | None:
        """Get the address linked to the logged-in Yasno account."""
        return self._account.address if self._account else None

    @property
    def account_balance(self) -> float | None:
        """Get the current balance/debt for the logged-in Yasno account."""
        if self._debt is not None:
            return self._debt.balance
        if self._contract is not None:
            return self._contract.debt
        return None

    @property
    def account_last_meter_reading_day(self) -> float | None:
        """Get the last submitted day-zone meter reading value."""
        if self._debt and self._debt.last_meter_reading:
            return self._debt.last_meter_reading.day_value
        return None

    @property
    def account_last_meter_reading_night(self) -> float | None:
        """Get the last submitted night-zone meter reading value."""
        if self._debt and self._debt.last_meter_reading:
            return self._debt.last_meter_reading.night_value
        return None

    @property
    def account_last_meter_reading_on(self) -> datetime.datetime | None:
        """Get the timestamp of the last submitted meter reading."""
        if self._debt and self._debt.last_meter_reading:
            return self._debt.last_meter_reading.created_on
        return None

    @property
    def account_last_meter_reading_owner(self) -> str | None:
        """Get who submitted the last meter reading (e.g. Client/Company)."""
        if self._debt and self._debt.last_meter_reading:
            return self._debt.last_meter_reading.owner
        return None

    @property
    def account_last_meter_reading_method(self) -> str | None:
        """Get how the last meter reading was submitted (as reported by Yasno)."""
        if self._debt and self._debt.last_meter_reading:
            return self._debt.last_meter_reading.reading_method
        return None

    @property
    def tariff_name(self) -> str | None:
        """
        Get the name of the account's current tariff plan.

        Translates known plan names via the "common" translation keys;
        falls back to the raw name as returned by Yasno's API for any
        plan name not in TARIFF_PLAN_NAME_TRANSLATION_KEYS.
        """
        if not self._tariff:
            return None
        raw_name = self._tariff.name
        translation_key = TARIFF_PLAN_NAME_TRANSLATION_KEYS.get(raw_name)
        if not translation_key:
            return raw_name
        fallback = TARIFF_PLAN_NAME_TEXT_FALLBACKS.get(raw_name, raw_name)
        return self.translations.get(translation_key, fallback)

    @property
    def tariff_price_day(self) -> float | None:
        """Get the current day-zone price per kWh (UAH) for the account."""
        if not self._tariff:
            return None
        return self._tariff.price_for_zone(dt_utils.now(), TARIFF_ZONE_DAY)

    @property
    def tariff_price_night(self) -> float | None:
        """Get the current night-zone price per kWh (UAH) for the account."""
        if not self._tariff:
            return None
        return self._tariff.price_for_zone(dt_utils.now(), TARIFF_ZONE_NIGHT)

    @property
    def tariff_distribution_price(self) -> float | None:
        """Get the DSO's distribution (transmission grid) price per kWh (UAH)."""
        return self._tariff.distribution_price if self._tariff else None

    @property
    def tariff_transfer_price(self) -> float | None:
        """Get the DSO's transfer (transport) price per kWh (UAH)."""
        return self._tariff.transfer_price if self._tariff else None

    def get_outage_at(
        self,
        api: BaseYasnoApi,
        at: datetime.datetime,
    ) -> OutageEvent | None:
        """Get an outage event at a given time from provided API."""
        try:
            event = api.get_current_event(at)
        except Exception:  # noqa: BLE001
            LOGGER.warning("Failed to get current outage", exc_info=True)
            return None
        if not is_outage_event(event):
            return None
        return event

    def get_planned_outage_at(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the planned outage event at a given time."""
        return self.get_outage_at(self.api.planned, at)

    def get_probable_outage_at(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the probable outage event at a given time."""
        return self.get_outage_at(self.api.probable, at)

    def get_events_between(
        self,
        api: BaseYasnoApi,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get outage events within the date range for provided API."""
        try:
            events = api.get_events_between(start_date, end_date)
        except Exception:  # noqa: BLE001
            LOGGER.warning(
                'Failed to get events between "%s" -> "%s"',
                start_date,
                end_date,
                exc_info=True,
            )
            return []

        filtered_events = [event for event in events if is_outage_event(event)]
        return sorted(filtered_events, key=lambda event: event.start)

    def get_planned_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get all planned events (filtering out NOT_PLANNED)."""
        return self.get_events_between(self.api.planned, start_date, end_date)

    def get_probable_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get all probable outage events within the date range."""
        return self.get_events_between(self.api.probable, start_date, end_date)

    def get_planned_dates(self) -> list[datetime.date]:
        """Get dates with planned outages."""
        return self.api.planned.get_planned_dates()

    def get_merged_outages(
        self,
        api: BaseYasnoApi,
        start_date: datetime.datetime,
        lookahead_days: int,
    ) -> list[OutageEvent]:
        """Get merged outage events for a lookahead period."""
        end_date = start_date + datetime.timedelta(days=lookahead_days)
        events = self.get_events_between(api, start_date, end_date)
        return merge_consecutive_outages(events)
