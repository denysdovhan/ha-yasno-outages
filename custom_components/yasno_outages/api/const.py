"""API constants for Yasno outages."""

from typing import Final

# Event names
EVENT_NAME_OUTAGE: Final = "Definite"
EVENT_NAME_NOT_PLANNED: Final = "NotPlanned"

# API Endpoints
REGIONS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/regions"
)
PLANNED_OUTAGES_ENDPOINT: Final = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages"
PROBABLE_OUTAGES_ENDPOINT: Final = "https://app.yasno.ua/api/blackout-service/public/shutdowns/probable-outages?regionId={region_id}&dsoId={dso_id}"

# API Status values
API_STATUS_SCHEDULE_APPLIES: Final = "ScheduleApplies"
API_STATUS_WAITING_FOR_SCHEDULE: Final = "WaitingForSchedule"
API_STATUS_EMERGENCY_SHUTDOWNS: Final = "EmergencyShutdowns"

# API Block names
API_KEY_TODAY: Final = "today"
API_KEY_TOMORROW: Final = "tomorrow"
API_KEY_STATUS: Final = "status"
API_KEY_DATE: Final = "date"
API_KEY_UPDATED_ON: Final = "updatedOn"
