"""Confirmed hourly schedules for Sumy from Alerts Energy."""

from typing import TYPE_CHECKING, override

from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_utils

from custom_components.svitlo_yeah.api.alerts_energy import AlertsEnergyClient
from custom_components.svitlo_yeah.const import (
    CONF_GROUP,
    DOMAIN,
    ISSUE_ALERTS_ENERGY_GROUP_REQUIRED,
    TRANSLATION_KEY_EVENT_PLANNED_OUTAGE,
    common_translation_key,
)
from custom_components.svitlo_yeah.models import (
    AlertsEnergyProvider,
    ConnectivityState,
    PlannedOutageEventType,
)

from .coordinator import IntegrationCoordinator

if TYPE_CHECKING:
    from homeassistant.components.calendar import CalendarEvent
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


class AlertsEnergyCoordinator(IntegrationCoordinator):
    """Keep dated confirmed schedules, including when the source is unreachable."""

    api: AlertsEnergyClient
    provider: AlertsEnergyProvider
    provider_id = "sumy"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Set up the public Sumy source without credentials."""
        super().__init__(hass, config_entry)
        self.provider = AlertsEnergyProvider()
        group = config_entry.data.get(CONF_GROUP)
        self.group = group or "?"
        self.api = AlertsEnergyClient(hass, group=group)

    @property
    @override
    def region_name(self) -> str:
        """Name Sumy in the language of Home Assistant."""
        return self.translations.get(common_translation_key("sumy"), "sumy")

    @property
    @override
    def provider_name(self) -> str:
        """Name the source without any personal information."""
        return "Alerts Energy"

    @property
    @override
    def event_name_map(self) -> dict:
        """Only confirmed planned events are supported."""
        return {
            PlannedOutageEventType.DEFINITE: self.translations.get(
                TRANSLATION_KEY_EVENT_PLANNED_OUTAGE
            ),
        }

    @override
    async def _async_fetch(self) -> bool:
        """Ask only for the configured hourly schedule."""
        if not self.config_entry.data.get(CONF_GROUP):
            return False
        return await self.api.fetch_data()

    @override
    async def _async_use_answer(self, answer: bool) -> None:
        """Report failures without making entities unavailable."""
        self._set_last_fetch_failed(failed=not answer)
        await self._async_update_group_listed(listed=self.api.group_listed)
        if not self.config_entry.data.get(CONF_GROUP):
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"{ISSUE_ALERTS_ENERGY_GROUP_REQUIRED}_{self.config_entry.entry_id}",
                is_fixable=False,
                is_persistent=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_ALERTS_ENERGY_GROUP_REQUIRED,
                translation_placeholders={
                    "integration": await self._async_integration_title()
                },
            )

    @override
    def _source_data(self) -> dict | None:
        """Keep this group's normalized, explicitly dated schedule."""
        return self.api.source_data()

    @override
    def _restore_source_data(self, source: dict) -> None:
        """Restore this group only, including the old E-Svitlo cache."""
        self.api.restore_source_data(source)

    @override
    async def _async_restore(self, stored: dict) -> None:
        """Accept a legacy group kept only in the Store envelope."""
        source = stored.get("source")
        if (
            isinstance(source, dict)
            and "disconnections" in source
            and source.get("group") is None
            and stored.get("group") == self.api.group
            and self.api.group is not None
        ):
            stored = {**stored, "source": {**source, "group": self.api.group}}
        await super()._async_restore(stored)

    @property
    @override
    def current_state(self) -> str | None:
        """Unknown data never claims that the electricity is on."""
        if self.group_listed is False:
            return None
        return super().current_state

    @override
    def _event_to_state(self, event: CalendarEvent | None) -> ConnectivityState | None:
        """Show confirmed outages and normal only for a complete known day."""
        if event is not None and event.uid == PlannedOutageEventType.DEFINITE.value:
            return ConnectivityState.STATE_PLANNED_OUTAGE
        if self.api.has_complete_day(dt_utils.now()):
            return ConnectivityState.STATE_NORMAL
        return None

    @property
    @override
    def _group_str(self) -> str:
        """Keep the existing Sumy calendar summaries."""
        return ""
