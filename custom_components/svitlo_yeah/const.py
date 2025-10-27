"""Constants for the Svitlo Yeah integration."""

from typing import Final

DOMAIN: Final = "svitlo_yeah"
NAME: Final = "Svitlo Yeah | Світло Є"

# Configuration option
CONF_REGION: Final = "region"
CONF_PROVIDER: Final = "provider"
CONF_GROUP: Final = "group"

# Provider name simplification
PROVIDER_DTEK_FULL: Final = "ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ"
PROVIDER_DTEK_SHORT: Final = "ДТЕК"

# Consts
UPDATE_INTERVAL: Final = 15

# Values
STATE_NORMAL: Final = "normal"
STATE_OUTAGE: Final = "outage"

# Event names
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
    "component.svitlo_yeah.common.event_name_planned_outage"
)

# Device
DEVICE_TRANSLATION_KEY = DOMAIN
DEVICE_MANUFACTURER = NAME
