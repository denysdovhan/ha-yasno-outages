"""Models for Svitlo Yeah."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from .providers import AlertsEnergyProvider, YasnoProvider

if TYPE_CHECKING:
    import datetime

__all__ = [
    "AlertsEnergyProvider",
    "ConnectivityState",
    "PlannedOutageEvent",
    "PlannedOutageEventType",
    "YasnoPlannedOutageDayStatus",
    "YasnoProvider",
    "YasnoRegion",
]


class YasnoPlannedOutageDayStatus(StrEnum):
    """Outage day status."""

    STATUS_SCHEDULE_APPLIES = "ScheduleApplies"
    STATUS_WAITING_FOR_SCHEDULE = "WaitingForSchedule"
    STATUS_EMERGENCY_SHUTDOWNS = "EmergencyShutdowns"


class PlannedOutageEventType(StrEnum):
    """Outage event types."""

    DEFINITE = "Definite"
    NOT_PLANNED = "NotPlanned"
    EMERGENCY = "Emergency"
    # This one does not exist in the API
    # It is only to create scheduled events
    SCHEDULED = "Scheduled"


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


@dataclass
class YasnoRegion:
    """Yasno region data."""

    id: int  # 25
    name: str  # Київ
    dsos: list[YasnoProvider] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> YasnoRegion:
        """Create instance from dict data."""
        output = cls(id=data["id"], name=data["value"])
        output.dsos = [
            YasnoProvider.from_dict(
                data=_, region_id=output.id, region_name=output.name
            )
            for _ in data["dsos"]
        ]
        return output
