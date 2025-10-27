"""Svitlo Yeah entity."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_MANUFACTURER, DEVICE_NAME_TRANSLATION_KEY, DOMAIN
from .coordinator import IntegrationCoordinator


class IntegrationEntity(CoordinatorEntity[IntegrationCoordinator]):
    """Common logic for Svitlo Yeah entity."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        return DeviceInfo(
            translation_key=DEVICE_NAME_TRANSLATION_KEY,
            translation_placeholders={
                "region": self.coordinator.region_name,
                "provider": self.coordinator.provider_name,
                "group": str(self.coordinator.group),
            },
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            manufacturer=DEVICE_MANUFACTURER,
            entry_type=DeviceEntryType.SERVICE,
        )
