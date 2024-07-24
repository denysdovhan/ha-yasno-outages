"""Yasno Outages entity."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YasnoOutagesCoordinator


class YasnoOutagesEntity(CoordinatorEntity[YasnoOutagesCoordinator]):
    """Common logic for Yasno Outages entity."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        return DeviceInfo(
            translation_key="yasno_outages",
            translation_placeholders={"group": str(self.coordinator.group)},
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            manufacturer="Yasno",
            entry_type=DeviceEntryType.SERVICE,
        )
