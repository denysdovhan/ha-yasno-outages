"""Constants for the Svitlo Yeah integration."""

from typing import Final

# Do not commit as True
DEBUG: Final = False

DOMAIN: Final = "svitlo_yeah"
NAME: Final = "Svitlo Yeah | Світло Є"

# Configuration option
CONF_REGION: Final = "region"
CONF_PROVIDER: Final = "provider"
CONF_GROUP: Final = "group"
CONF_PROVIDER_TYPE: Final = "provider_type"

# Provider types
PROVIDER_TYPE_YASNO: Final = "yasno"
PROVIDER_TYPE_DTEK: Final = "dtek"

# Special region identifier for Regions
REGION_SELECTION_DTEK_KEY: Final = "region_dtek"

# Provider name simplification
PROVIDER_DTEK_FULL: Final = "ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ"
PROVIDER_DTEK_SHORT: Final = "ДТЕК"

# Consts
UPDATE_INTERVAL: Final = 15

# API Endpoints
REGIONS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/regions"
)
PLANNED_OUTAGES_ENDPOINT: Final = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages"

# API Block names
BLOCK_KEY_STATUS: Final = "status"

# Keys
TRANSLATION_KEY_EVENT_PLANNED_OUTAGE: Final = (
    "component.svitlo_yeah.common.event_name_planned_outage"
)
TRANSLATION_KEY_EVENT_EMERGENCY_OUTAGE: Final = (
    "component.svitlo_yeah.common.event_name_emergency_outage"
)

# Device
DEVICE_NAME_YASNO_TRANSLATION_KEY = "device_name_yasno"
DEVICE_NAME_DTEK_TRANSLATION_KEY = "device_name_dtek"
DEVICE_MANUFACTURER = NAME

DTEK_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "uk,en-US;q=0.8,en;q=0.5,ru;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.google.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101"
    " Firefox/144.0",
}
