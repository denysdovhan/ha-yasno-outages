"""Helper utilities for Yasno outages integration."""

from __future__ import annotations

from .api import OutageEvent


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
