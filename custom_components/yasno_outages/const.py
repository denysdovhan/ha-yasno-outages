"""Constants for the Yasno Outages integration."""

from typing import Final

DOMAIN: Final = "yasno_outages"
NAME: Final = "Yasno Outages"

# Configuration option
CONF_REGION: Final = "region"
CONF_PROVIDER: Final = "provider"
CONF_GROUP: Final = "group"
CONF_CITY: Final = "city"  # Deprecated, use CONF_REGION
CONF_SERVICE: Final = "service"  # Deprecated, use CONF_PROVIDER

# Provider name simplification
PROVIDER_DTEK_FULL: Final = "ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ"
PROVIDER_DTEK_SHORT: Final = "ДТЕК"

# Consts
UPDATE_INTERVAL: Final = 15

# Values
STATE_NORMAL: Final = "normal"
STATE_OUTAGE: Final = "outage"

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
# Text fallbacks
PLANNED_OUTAGE_TEXT_FALLBACK: Final = "Planned Outage"
PROBABLE_OUTAGE_TEXT_FALLBACK: Final = "Probable Outage"
