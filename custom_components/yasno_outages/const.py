"""Constants for the Yasno Outages integration."""

from typing import Final

DOMAIN: Final = "yasno_outages"

# Configuration option
CONF_GROUP: Final = "group"

# Attributes
ATTR_GROUP: Final = "group"

# Keys
TRANSLATION_KEY_CALENDAR: Final = f"{DOMAIN}_calendar"
TRANSLATION_KEY_CALENDAR_EVENT_OFF: Final = (
    f"component.{DOMAIN}.states.{TRANSLATION_KEY_CALENDAR}.off"
)
TRANSLATION_KEY_CALENDAR_EVENT_MAYBE: Final = (
    f"component.{DOMAIN}.states.{TRANSLATION_KEY_CALENDAR}.maybe"
)
