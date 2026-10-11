"""Constants for the Svitlo Yeah integration."""

from typing import Final
from zoneinfo import ZoneInfo

DOMAIN: Final = "svitlo_yeah"
NAME: Final = "Svitlo Yeah | Світло Є"
CONFIG_ENTRY_VERSION: Final = 2

# Configuration option
CONF_REGION: Final = "region"
CONF_PROVIDER: Final = "provider"
CONF_GROUP: Final = "group"
CONF_ACCOUNT_ID: Final = "account_id"
CONF_ADDRESS_STR: Final = "address_str"
CONF_PROVIDER_TYPE: Final = "provider_type"

# Provider types
PROVIDER_TYPE_YASNO: Final = "yasno"
PROVIDER_TYPE_DTEK_JSON: Final = "dtek_json"
PROVIDER_TYPE_E_SVITLO: Final = "e-svitlo"
PROVIDER_TYPE_ALERTS_ENERGY: Final = "alerts_energy"

# Provider name simplification
PROVIDER_DTEK_FULL: Final = "ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ"
PROVIDER_DTEK_SHORT: Final = "ДТЕК"

TZ_UA = ZoneInfo("Europe/Kyiv")

# Costants
UPDATE_INTERVAL: Final = 15
DTEK_FRESH_DATA_DAYS: Final = 2

# The schedules count the hours of one day; 23:59 stands for the end of a day
HOURS_IN_DAY: Final = 24
MINUTES_IN_DAY: Final = HOURS_IN_DAY * 60
LAST_HOUR: Final = 23
LAST_MINUTE: Final = 59

# API Endpoints
YASNO_REGIONS_ENDPOINT: Final = (
    "https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/regions"
)
YASNO_PLANNED_OUTAGES_ENDPOINT: Final = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages"

# API Block names
BLOCK_KEY_STATUS: Final = "status"

# Translation Keys
DEVICE_NAME_YASNO_TRANSLATION_KEY = "device_name_yasno"
DEVICE_NAME_DTEK_TRANSLATION_KEY = "device_name_dtek"
DEVICE_MANUFACTURER = NAME
DEVICE_NAME_ALERTS_ENERGY_TRANSLATION_KEY = "device_name_alerts_energy"
PROVIDER_TO_DEVICE_NAME_MAP: Final = {
    PROVIDER_TYPE_YASNO: DEVICE_NAME_YASNO_TRANSLATION_KEY,
    PROVIDER_TYPE_DTEK_JSON: DEVICE_NAME_DTEK_TRANSLATION_KEY,
    PROVIDER_TYPE_ALERTS_ENERGY: DEVICE_NAME_ALERTS_ENERGY_TRANSLATION_KEY,
}


def common_translation_key(name: str) -> str:
    """Return the key of a text of the common section, for example a region name."""
    return f"component.{DOMAIN}.common.{name}"


TRANSLATION_KEY_EVENT_PLANNED_OUTAGE: Final = common_translation_key(
    "event_name_planned_outage"
)
TRANSLATION_KEY_EVENT_SCHEDULED_OUTAGE: Final = common_translation_key(
    "event_name_scheduled_outage"
)
TRANSLATION_KEY_EVENT_EMERGENCY_OUTAGE: Final = common_translation_key(
    "event_name_emergency_outage"
)
# Repair issue: the translation key, and the prefix of the issue id
ISSUE_GROUP_NOT_LISTED: Final = "group_not_listed"
ISSUE_ALERTS_ENERGY_GROUP_REQUIRED: Final = "alerts_energy_group_required"

ALERTS_ENERGY_URL: Final = (
    "https://alerts.energy/api/v1/source-registry/areas/sumska-oblast/shutdowns"
)
ALERTS_ENERGY_INITIATOR: Final = "sumska_oblast_oblenergo"

EVENT_DATA_CHANGED: Final = f"{DOMAIN}_data_changed"

DTEK_PROVIDER_URLS: dict[str, list[str]] = {
    "kyiv_region": [
        "https://github.com/Baskerville42/outage-data-ua/raw/main/data/kyiv-region.json",
    ],
    "dnipro": [
        "https://github.com/Baskerville42/outage-data-ua/raw/main/data/dnipro.json",
    ],
    "odesa": [
        "https://github.com/Baskerville42/outage-data-ua/raw/main/data/odesa.json",
    ],
    "khmelnytskyi": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Khmelnytskoblenerho.json",
    ],
    "ivano_frankivsk": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Prykarpattiaoblenerho.json",
    ],
    "uzhhorod": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Zakarpattiaoblenerho.json",
    ],
    "lviv": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Lvivoblenerho.json",
    ],
    "ternopil": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Ternopiloblenerho.json",
    ],
    "chernihiv": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Chernihivoblenergo.json",
    ],
    "zaporizhzhia": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Zaporizhzhiaoblenergo.json",
    ],
    "vinnytsia": [
        "https://github.com/olnet93/gpv-voe-vinnytsia/raw/main/data/Vinnytsiaoblenerho.json",
        "https://github.com/vn-progr/gpv-voe-vinnytsia/raw/main/data/Vinnytsiaoblenerho.json",
    ],
    "zhytomyr": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Zhytomyroblenergo.json",
    ],
    "poltava": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Poltavaoblenergo.json",
    ],
    "rivne": [
        "https://github.com/yaroslav2901/OE_OUTAGE_DATA/raw/main/data/Rivneoblenergo.json",
    ],
}
