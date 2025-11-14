"""Data models for Yasno outages API."""

import datetime
from dataclasses import dataclass
from enum import Enum


class OutageEventType(str, Enum):
    """Outage event types."""

    DEFINITE = "Definite"
    NOT_PLANNED = "NotPlanned"


@dataclass(frozen=True)
class OutageEvent:
    """Represents an outage event."""

    event_type: OutageEventType
    start: datetime.datetime
    end: datetime.datetime


@dataclass(frozen=True)
class ProbableOutageSlot:
    """Represents a probable outage time slot."""

    start: int  # Minutes from midnight
    end: int  # Minutes from midnight
    event_type: OutageEventType
