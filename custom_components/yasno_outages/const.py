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

# Provider name simplification
PROVIDER_DTEK_FULL: Final = "ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ"
PROVIDER_DTEK_SHORT: Final = "ДТЕК"

# Consts
UPDATE_INTERVAL: Final = 15  # minutes

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

# Status states
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
TRANSLATION_KEY_STATUS_SCHEDULE_APPLIES: Final = (
    f"component.{DOMAIN}.common.status_schedule_applies"
)
TRANSLATION_KEY_STATUS_WAITING_FOR_SCHEDULE: Final = (
    f"component.{DOMAIN}.common.status_waiting_for_schedule"
)
TRANSLATION_KEY_STATUS_EMERGENCY_SHUTDOWNS: Final = (
    f"component.{DOMAIN}.common.status_emergency_shutdowns"
)
# Text fallbacks
PLANNED_OUTAGE_TEXT_FALLBACK: Final = "Planned Outage"
PROBABLE_OUTAGE_TEXT_FALLBACK: Final = "Probable Outage"
STATUS_SCHEDULE_APPLIES_TEXT_FALLBACK: Final = "Schedule Applies"
STATUS_WAITING_FOR_SCHEDULE_TEXT_FALLBACK: Final = "Waiting for Schedule"
STATUS_EMERGENCY_SHUTDOWNS_TEXT_FALLBACK: Final = "Emergency Shutdowns"
