"""Init file for Svitlo Yeah integration."""

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_translations

from .const import (
    CONF_ACCOUNT_ID,
    CONF_ADDRESS_STR,
    CONF_GROUP,
    CONF_PROVIDER,
    CONF_PROVIDER_TYPE,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    ISSUE_ALERTS_ENERGY_GROUP_REQUIRED,
    NAME,
    PROVIDER_TYPE_ALERTS_ENERGY,
    PROVIDER_TYPE_DTEK_JSON,
    PROVIDER_TYPE_E_SVITLO,
    PROVIDER_TYPE_YASNO,
    common_translation_key,
)
from .coordinator.alerts_energy import AlertsEnergyCoordinator
from .coordinator.coordinator import (
    STORE_VERSION,
    group_not_listed_issue_id,
    store_key,
)
from .coordinator.dtek.json import DtekCoordinatorJson
from .coordinator.yasno import YasnoCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator.coordinator import SvitloYeahConfigEntry

LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SvitloYeahConfigEntry) -> bool:
    """Set up a new entry."""
    LOGGER.debug("Setup entry: %s", entry)
    provider_type = entry.data.get(CONF_PROVIDER_TYPE)

    if provider_type == PROVIDER_TYPE_DTEK_JSON:
        coordinator = DtekCoordinatorJson(hass, entry)
    elif provider_type == PROVIDER_TYPE_YASNO:
        coordinator = YasnoCoordinator(hass, entry)
    elif provider_type == PROVIDER_TYPE_ALERTS_ENERGY:
        coordinator = AlertsEnergyCoordinator(hass, entry)
    else:
        # Nothing can make the entry usable, so the user adds it again
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="unknown_provider_type",
            translation_placeholders={"provider_type": str(provider_type)},
        )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: SvitloYeahConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant,
    entry: SvitloYeahConfigEntry,
) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unload entry: %s", entry)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # The next setup asks the source again and creates the issue if needed.
        ir.async_delete_issue(hass, DOMAIN, group_not_listed_issue_id(entry.entry_id))
        if entry.data.get(CONF_PROVIDER_TYPE) == PROVIDER_TYPE_ALERTS_ENERGY:
            ir.async_delete_issue(
                hass, DOMAIN, f"{ISSUE_ALERTS_ENERGY_GROUP_REQUIRED}_{entry.entry_id}"
            )
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: SvitloYeahConfigEntry) -> None:
    """Delete the last data that the entry kept for a restart."""
    await Store(hass, STORE_VERSION, store_key(entry.entry_id)).async_remove()


def _sumy_group(value: object) -> str | None:
    """Accept only a concrete Sumy subgroup, never the old auto marker."""
    groups = {f"{queue}.{half}" for queue in range(1, 7) for half in (1, 2)}
    return value if isinstance(value, str) and value in groups else None


async def async_migrate_entry(
    hass: HomeAssistant, entry: SvitloYeahConfigEntry
) -> bool:
    """Replace only the old Sumy source, without asking either source."""
    if entry.version > CONFIG_ENTRY_VERSION:
        return False
    if entry.version == CONFIG_ENTRY_VERSION:
        return True
    if (
        entry.data.get(CONF_PROVIDER_TYPE) != PROVIDER_TYPE_E_SVITLO
        or entry.data.get(CONF_PROVIDER) != "sumy"
    ):
        hass.config_entries.async_update_entry(
            entry, version=CONFIG_ENTRY_VERSION, minor_version=1
        )
        return True

    if CONF_GROUP in entry.data:
        group = _sumy_group(entry.data[CONF_GROUP])
    else:
        try:
            stored = await Store(
                hass, STORE_VERSION, store_key(entry.entry_id)
            ).async_load()
        except Exception:  # corrupted or inaccessible legacy cache
            LOGGER.debug("Cannot read the legacy Sumy cache", exc_info=True)
            stored = None
        source = stored.get("source") if isinstance(stored, dict) else None
        source_group = source.get("group") if isinstance(source, dict) else None
        stored_group = stored.get("group") if isinstance(stored, dict) else None
        groups = [value for value in (source_group, stored_group) if value is not None]
        group = (
            _sumy_group(groups[0])
            if groups and all(value == groups[0] for value in groups)
            else None
        )

    private_keys = {CONF_USERNAME, CONF_PASSWORD, CONF_ACCOUNT_ID, CONF_ADDRESS_STR}
    data = {key: value for key, value in entry.data.items() if key not in private_keys}
    data[CONF_PROVIDER_TYPE] = PROVIDER_TYPE_ALERTS_ENERGY
    data.pop(CONF_GROUP, None)
    if group is not None:
        data[CONF_GROUP] = group
    options = {
        key: value for key, value in entry.options.items() if key not in private_keys
    }

    names = await async_get_translations(hass, hass.config.language, "common", [DOMAIN])
    provider_name = names.get(common_translation_key("sumy"), "sumy")
    title = entry.title
    if title in (
        NAME,
        "Sumy E-Svitlo",
        "Суми E-Svitlo",
        "Sumy and Oblast E-Svitlo",
        "Суми та область E-Svitlo",
    ):
        title = f"{provider_name} Alerts Energy {group or ''}".strip()
    for flow in list(entry.async_get_active_flows(hass, {SOURCE_REAUTH})):
        hass.config_entries.flow.async_abort(flow["flow_id"])
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        options=options,
        title=title,
        version=CONFIG_ENTRY_VERSION,
        minor_version=1,
    )
    return True
