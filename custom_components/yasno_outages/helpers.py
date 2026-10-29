"""Helper utilities for Yasno outages integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .api import OutageEvent
from .const import (
    CONF_ADDRESS_GROUP,
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_STREET_ID,
    LOCATION_CONFIG_KEYS,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


def build_address_data(
    config: Mapping[str, Any],
    *,
    region_id: int | None,
    provider_id: int | None,
    group: str | None,
) -> dict[str, Any]:
    """Bind a resolved group to the address and provider that validated it."""
    return {
        **{key: config[key] for key in LOCATION_CONFIG_KEYS if key in config},
        CONF_GROUP: group,
        CONF_ADDRESS_GROUP: {
            "region_id": region_id,
            "provider_id": provider_id,
            CONF_STREET_ID: config[CONF_STREET_ID],
            CONF_HOUSE_ID: config[CONF_HOUSE_ID],
            CONF_GROUP: group,
        }
        if group
        else None,
    }


def merge_consecutive_outages(events: list[OutageEvent]) -> list[OutageEvent]:
    """
    Merge consecutive outage events with identical type/source.

    Expects `events` pre-sorted and already filtered to outage events.
    """
    if not events:
        return []

    merged: list[OutageEvent] = []
    current_event = events[0]

    for next_event in events[1:]:
        if (
            current_event.end == next_event.start
            and current_event.event_type == next_event.event_type
            and current_event.source == next_event.source
        ):
            current_event = OutageEvent(
                start=current_event.start,
                end=next_event.end,
                event_type=current_event.event_type,
                source=current_event.source,
            )
        else:
            merged.append(current_event)
            current_event = next_event

    merged.append(current_event)

    return merged
