"""Constants for the Yasno Outages integration."""

from typing import Final

DOMAIN: Final = "yasno_outages"
NAME: Final = "Yasno Outages"
YASNO_GROUP_URL: Final = "https://static.yasno.ua/kyiv/outages"

# Configuration option
CONF_REGION: Final = "region"
CONF_PROVIDER: Final = "provider"
CONF_GROUP: Final = "group"
CONF_STREET_ID: Final = "street_id"
CONF_HOUSE_ID: Final = "house_id"
CONF_ADDRESS_NAME: Final = "address_name"
CONF_FILTER_PROBABLE: Final = "filter_probable"
CONF_STATUS_ALL_DAY_EVENTS: Final = "status_all_day_events"
CONF_CITY: Final = "city"  # Deprecated, use CONF_REGION
CONF_SERVICE: Final = "service"  # Deprecated, use CONF_PROVIDER

# Config-flow step fields
CONF_STEP_SETUP_MODE: Final = "setup_mode"
CONF_STEP_STREET_QUERY: Final = "street_query"
CONF_STEP_HOUSE_QUERY: Final = "house_query"
CONF_STEP_STREET: Final = "street"
CONF_STEP_HOUSE: Final = "house"

# Login mode: public (region/provider/group only) vs authenticated account login
CONF_LOGIN_MODE: Final = "login_mode"
LOGIN_MODE_PUBLIC: Final = "public"
LOGIN_MODE_ACCOUNT: Final = "account"

# Authenticated account login configuration
CONF_PHONE_NUMBER: Final = "phone_number"
CONF_MESSAGE_TYPE: Final = "message_type"
CONF_ACCESS_TOKEN: Final = "access_token"  # noqa: S105
CONF_REFRESH_TOKEN: Final = "refresh_token"  # noqa: S105
CONF_TOKEN_EXPIRES_AT: Final = "token_expires_at"  # noqa: S105
CONF_ACCOUNT_ID: Final = "account_id"

# Provider name simplification
PROVIDER_DTEK_FULL: Final = "ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ"
PROVIDER_DTEK_SHORT: Final = "ДТЕК"

# Consts
UPDATE_INTERVAL: Final = 15  # minutes

# Refresh the access token this many minutes before it actually expires
AUTH_TOKEN_REFRESH_MARGIN: Final = 5  # minutes

# Horizon constants for event lookahead
PLANNED_OUTAGE_LOOKAHEAD = 1  # day
PROBABLE_OUTAGE_LOOKAHEAD = 7  # days

# Values
STATE_NORMAL: Final = "normal"
STATE_OUTAGE: Final = "outage"

# Attribute keys
ATTR_EVENT_TYPE: Final = "event_type"
ATTR_EVENT_START: Final = "event_start"
ATTR_EVENT_END: Final = "event_end"
ATTR_METER_READING_OWNER: Final = "owner"
ATTR_METER_READING_METHOD: Final = "reading_method"

# Status states
STATE_STATUS_NO_OUTAGES: Final = "no_outages"
STATE_STATUS_SCHEDULE_APPLIES: Final = "schedule_applies"
STATE_STATUS_WAITING_FOR_SCHEDULE: Final = "waiting_for_schedule"
STATE_STATUS_EMERGENCY_SHUTDOWNS: Final = "emergency_shutdowns"

# Keys
TRANSLATION_KEY_EVENT_PLANNED_OUTAGE: Final = (
    f"component.{DOMAIN}.common.planned_electricity_outage"
)
TRANSLATION_KEY_EVENT_PROBABLE_OUTAGE: Final = (
    f"component.{DOMAIN}.common.probable_electricity_outage"
)
TRANSLATION_KEY_STATUS_NO_OUTAGES: Final = (
    f"component.{DOMAIN}.common.status_no_outages"
)
TRANSLATION_KEY_STATUS_SCHEDULE_APPLIES: Final = (
    f"component.{DOMAIN}.common.status_schedule_applies"
)
TRANSLATION_KEY_STATUS_WAITING_FOR_SCHEDULE: Final = (
    f"component.{DOMAIN}.common.status_waiting_for_schedule"
)
TRANSLATION_KEY_STATUS_EMERGENCY_SHUTDOWNS: Final = (
    f"component.{DOMAIN}.common.status_emergency_shutdowns"
)
TRANSLATION_KEY_TARIFF_PLAN_WITH_ELECTRIC_HEATING: Final = (
    f"component.{DOMAIN}.common.tariff_plan_with_electric_heating"
)
# Text fallbacks
PLANNED_OUTAGE_TEXT_FALLBACK: Final = "Planned Outage"
PROBABLE_OUTAGE_TEXT_FALLBACK: Final = "Probable Outage"
STATUS_NO_OUTAGES_TEXT_FALLBACK: Final = "No Outages"
STATUS_SCHEDULE_APPLIES_TEXT_FALLBACK: Final = "Schedule Applies"
STATUS_WAITING_FOR_SCHEDULE_TEXT_FALLBACK: Final = "Waiting for Schedule"
STATUS_EMERGENCY_SHUTDOWNS_TEXT_FALLBACK: Final = "Emergency Shutdowns"
TARIFF_PLAN_WITH_ELECTRIC_HEATING_TEXT_FALLBACK: Final = "With Electric Heating"

# Yasno's API returns tariff plan names as free-text Ukrainian strings (no
# stable plan code), so only known plan names can be translated here. Any
# plan name not in this map is shown as-is (raw Ukrainian text from the API).
TARIFF_PLAN_NAME_TRANSLATION_KEYS: Final[dict[str, str]] = {
    "З електроопаленням": TRANSLATION_KEY_TARIFF_PLAN_WITH_ELECTRIC_HEATING,  # noqa: RUF001
}
TARIFF_PLAN_NAME_TEXT_FALLBACKS: Final[dict[str, str]] = {
    "З електроопаленням": TARIFF_PLAN_WITH_ELECTRIC_HEATING_TEXT_FALLBACK,  # noqa: RUF001
}
