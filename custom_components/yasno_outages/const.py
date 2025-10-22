"""Constants for the Yasno Outages integration."""

from typing import Final

DOMAIN: Final = "yasno_outages"
NAME: Final = "Yasno Outages"

# Configuration option
CONF_CITY: Final = "city"
CONF_SERVICE: Final = "service"
CONF_GROUP: Final = "group"

# Consts
UPDATE_INTERVAL: Final = 15

# Values
STATE_ON: Final = "on"
STATE_OFF: Final = "off"
STATE_MAYBE: Final = "maybe"

# Event names
EVENT_NAME_OFF: Final = "Definite"
EVENT_NAME_MAYBE: Final = "NotPlanned"

# API Endpoints
REGIONS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/regions"
)
PLANNED_OUTAGES_ENDPOINT: Final = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages"

# Time constants
MINUTES_PER_DAY: Final = 1440
HOURS_PER_DAY_AND_ONE: Final = 25  # Special case for 24:00 handling

# API Status values
STATUS_SCHEDULE_APPLIES: Final = "ScheduleApplies"
STATUS_WAITING_FOR_SCHEDULE: Final = "WaitingForSchedule"

# Keys
TRANSLATION_KEY_EVENT_OFF: Final = f"component.{DOMAIN}.common.electricity_off"
TRANSLATION_KEY_EVENT_MAYBE: Final = f"component.{DOMAIN}.common.electricity_maybe"
