"""
Diagnostics support for Yasno Outages.

Learn more about diagnostics:
https://developers.home-assistant.io/docs/core/integration_diagnostics
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import (
    CONF_FILTER_PROBABLE,
    CONF_GROUP,
    CONF_PROVIDER,
    CONF_REGION,
    CONF_STATUS_ALL_DAY_EVENTS,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import YasnoOutagesConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: YasnoOutagesConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    api = entry.runtime_data.api
    data = entry.data

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "domain": entry.domain,
            "title": entry.title,
            "state": str(entry.state),
            "data": {
                "region": data.get(CONF_REGION),
                "provider": data.get(CONF_PROVIDER),
                "group": data.get(CONF_GROUP),
                "filter_probable": data.get(CONF_FILTER_PROBABLE),
                "status_all_day_events": data.get(CONF_STATUS_ALL_DAY_EVENTS),
            },
            "options": {
                "region": entry.options.get(CONF_REGION),
                "provider": entry.options.get(CONF_PROVIDER),
                "group": entry.options.get(CONF_GROUP),
                "filter_probable": entry.options.get(CONF_FILTER_PROBABLE),
                "status_all_day_events": entry.options.get(CONF_STATUS_ALL_DAY_EVENTS),
            },
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
            "region": coordinator.region,
            "region_id": coordinator.region_id,
            "provider": coordinator.provider,
            "provider_id": coordinator.provider_id,
            "provider_name": coordinator.provider_name,
            "group": coordinator.group,
            "filter_probable": coordinator.filter_probable,
            "status_all_day_events": coordinator.status_all_day_events,
            "current_state": coordinator.current_state,
            "status_today": coordinator.status_today,
            "status_tomorrow": coordinator.status_tomorrow,
            "schedule_updated_on": coordinator.schedule_updated_on.isoformat(),
            "next_planned_outage": coordinator.next_planned_outage.isoformat(),
            "next_probable_outage": coordinator.next_probable_outage.isoformat(),
            "next_connectivity": coordinator.next_connectivity.isoformat(),
        },
        "api": {
            "region_id": api.planned.region_id,
            "provider_id": api.planned.provider_id,
            "group": api.planned.group,
            "regions_data": api.regions_data,
            "planned_outages_data": api.planned.planned_outages_data,
            "probable_outages_data": api.probable.probable_outages_data,
        },
        "error": {
            "last_exception": (
                str(coordinator.last_exception) if coordinator.last_exception else None
            ),
        },
    }
