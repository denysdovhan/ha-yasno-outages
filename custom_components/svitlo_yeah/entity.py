"""Svitlo Yeah entity."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PROVIDER_TYPE,
    DEVICE_MANUFACTURER,
    DEVICE_NAME_DTEK_TRANSLATION_KEY,
    DEVICE_NAME_YASNO_TRANSLATION_KEY,
    DOMAIN,
    PROVIDER_TYPE_DTEK,
)
from .coordinator.dtek import DtekCoordinator
from .coordinator.yasno import YasnoCoordinator


class IntegrationEntity(CoordinatorEntity[YasnoCoordinator | DtekCoordinator]):
    """Common logic for Svitlo Yeah entity."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        provider_type = self.coordinator.config_entry.options.get(
            CONF_PROVIDER_TYPE,
            self.coordinator.config_entry.data.get(CONF_PROVIDER_TYPE),
        )

        translation_key = (
            DEVICE_NAME_DTEK_TRANSLATION_KEY
            if provider_type == PROVIDER_TYPE_DTEK
            else DEVICE_NAME_YASNO_TRANSLATION_KEY
        )

        return DeviceInfo(
            translation_key=translation_key,
            translation_placeholders={
                "region": self.coordinator.region_name,
                "provider": self.coordinator.provider_name,
                "group": str(self.coordinator.group),
            },
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            manufacturer=DEVICE_MANUFACTURER,
            entry_type=DeviceEntryType.SERVICE,
        )
