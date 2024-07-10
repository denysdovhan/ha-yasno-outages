"""Constants for the Yasno Outages integration."""

from typing import Final

DOMAIN: Final = "yasno_outages"
NAME: Final = "Yasno Outages"

# Configuration option
CONF_GROUP: Final = "group"

# Defaults
DEFAULT_GROUP: Final = "1"

# Consts
UPDATE_INTERVAL: Final = 60

# Values
STATE_ON: Final = "on"
STATE_OFF: Final = "off"
STATE_MAYBE: Final = "maybe"

# File paths
CALENDAR_PATH = "schedules/group-{group}.ics"

# Keys
TRANSLATION_KEY_EVENT_OFF: Final = f"component.{DOMAIN}.common.electricity_off"
TRANSLATION_KEY_EVENT_MAYBE: Final = f"component.{DOMAIN}.common.electricity_maybe"
