"""Models for Svitlo Yeah."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime


class YasnoPlannedOutageDayStatus(StrEnum):
    """Outage day status."""

    STATUS_SCHEDULE_APPLIES = "ScheduleApplies"
    STATUS_EMERGENCY_SHUTDOWNS = "EmergencyShutdowns"


class PlannedOutageEventType(StrEnum):
    """Outage event types."""

    DEFINITE = "Definite"
    NOT_PLANNED = "NotPlanned"
    EMERGENCY = "Emergency"


class ConnectivityState(StrEnum):
    """Connectivity state."""

    STATE_EMERGENCY = "emergency"
    STATE_NORMAL = "normal"
    STATE_PLANNED_OUTAGE = "planned_outage"


@dataclass(frozen=True)
class PlannedOutageEvent:
    """Represents an outage event."""

    event_type: PlannedOutageEventType
    start: datetime.datetime | datetime.date
    end: datetime.datetime | datetime.date
    all_day: bool = False
