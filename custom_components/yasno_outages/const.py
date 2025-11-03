"""Constants for the Yasno Outages integration."""

from typing import Final

DOMAIN: Final = "yasno_outages"
NAME: Final = "Yasno Outages"

# Configuration option
CONF_REGION: Final = "region"
CONF_SERVICE: Final = "service"
CONF_GROUP: Final = "group"
CONF_CITY: Final = "city"  # Deprecated, use CONF_REGION

# Provider name simplification
PROVIDER_DTEK_FULL: Final = "ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ"
PROVIDER_DTEK_SHORT: Final = "ДТЕК"

# Consts
UPDATE_INTERVAL: Final = 15

# Values
OUTAGE_STATE_NORMAL: Final = "normal"
OUTAGE_STATE_OUTAGE: Final = "outage"
OUTAGE_STATE_POSSIBLE: Final = "possible"

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
STATUS_WAITING_FOR_SCHEDULE: Final = "WaitingForSchedule"

# Keys
TRANSLATION_KEY_EVENT_OFF: Final = f"component.{DOMAIN}.common.electricity_off"
TRANSLATION_KEY_EVENT_MAYBE: Final = f"component.{DOMAIN}.common.electricity_maybe"
