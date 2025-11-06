"""Custom types for yasno_outages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import YasnoOutagesApi
    from .coordinator import YasnoOutagesCoordinator


type YasnoOutagesConfigEntry = ConfigEntry[YasnoOutagesData]


@dataclass
class YasnoOutagesData:
    """Data for the Yasno Outages integration."""

    api: YasnoOutagesApi
    coordinator: YasnoOutagesCoordinator
    integration: Integration
