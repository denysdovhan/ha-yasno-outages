"""Data models for Yasno outages API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class YasnoApiError(Exception):
    """Raised when Yasno API request fails."""


class YasnoNotFoundError(YasnoApiError):
    """Raised when Yasno API returns 404."""


class OutageEventType(StrEnum):
    """Outage event types."""

    DEFINITE = "Definite"
    NOT_PLANNED = "NotPlanned"


class OutageSource(StrEnum):
    """Source type for outage events."""

    PLANNED = "planned"
    PROBABLE = "probable"


@dataclass(frozen=True)
class OutageEvent:
    """Represents an outage event."""

    event_type: OutageEventType
    start: datetime
    end: datetime
    source: OutageSource


@dataclass(frozen=True)
class OutageSlot:
    """Represents an outage time slot template."""

    start: int  # Minutes from midnight
    end: int  # Minutes from midnight
    event_type: OutageEventType
