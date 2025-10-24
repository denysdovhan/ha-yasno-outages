"""Constants for the Yasno Outages integration."""

from typing import Final

DOMAIN: Final = "yasno_outages"
NAME: Final = "Yasno Outages"

# Configuration option
CONF_REGION: Final = "region"
CONF_PROVIDER: Final = "provider"
CONF_GROUP: Final = "group"
CONF_CITY: Final = "city"  # Deprecated, use CONF_REGION

# Provider name simplification
PROVIDER_DTEK_FULL: Final = "ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ"
PROVIDER_DTEK_SHORT: Final = "ДТЕК"

# Consts
UPDATE_INTERVAL: Final = 15

# Values
STATE_NORMAL: Final = "normal"
STATE_OUTAGE: Final = "outage"

# Event names
EVENT_NAME_NORMAL: Final = "NotPlanned"
EVENT_NAME_OUTAGE: Final = "Definite"

# API Endpoints
REGIONS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/regions"
)
PLANNED_OUTAGES_ENDPOINT: Final = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages"

# API Status values
STATUS_SCHEDULE_APPLIES: Final = "ScheduleApplies"

# API Block names
BLOCK_NAME_TODAY: Final = "today"
BLOCK_NAME_TOMORROW: Final = "tomorrow"
BLOCK_KEY_STATUS: Final = "status"

# Keys
TRANSLATION_KEY_EVENT_OUTAGE: Final = (
    f"component.{DOMAIN}.common.event_names.planned_outage"
)
TRANSLATION_KEY_EVENT_NORMAL: Final = f"component.{DOMAIN}.common.event_names.normal"
