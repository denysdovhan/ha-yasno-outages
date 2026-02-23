"""Tests for repairs flows."""

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.yasno_outages.const import (
    CONF_ADDRESS_NAME,
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_PROVIDER,
    CONF_REGION,
    CONF_STREET_ID,
    DOMAIN,
)
from custom_components.yasno_outages.repairs import (
    StaleAddressRepairFlow,
    async_create_fix_flow,
    async_create_stale_address_issue,
)


def _build_entry():
    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.title = "Yasno Kyiv Test"
    entry.data = {
        CONF_REGION: "Київ",
        CONF_PROVIDER: "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",
        CONF_GROUP: "1.1",
    }
    entry.options = {}
    return entry


async def test_create_stale_address_issue_is_fixable():
    """Stale address issue is created as fixable with entry id data."""
    hass = MagicMock()
    entry = _build_entry()

    with patch(
        "custom_components.yasno_outages.repairs.ir.async_create_issue"
    ) as create_issue:
        await async_create_stale_address_issue(hass, entry)

    call = create_issue.call_args
    assert call.kwargs["is_fixable"] is True
    assert call.kwargs["translation_key"] == "stale_address_ids"
    assert call.kwargs["data"] == {"entry_id": entry.entry_id}


async def test_create_fix_flow_returns_stale_address_flow():
    """Fix flow factory returns stale-address repair flow."""
    hass = MagicMock()
    entry = _build_entry()
    hass.config_entries.async_get_entry.return_value = entry

    flow = await async_create_fix_flow(
        hass,
        issue_id=f"stale_address_ids_{entry.entry_id}",
        data={"entry_id": entry.entry_id},
    )

    assert isinstance(flow, StaleAddressRepairFlow)


async def test_repair_init_ignores_empty_user_input():
    """Init step should not crash when user_input is an empty dict."""
    entry = _build_entry()
    flow = StaleAddressRepairFlow(entry)
    flow.handler = DOMAIN
    flow.flow_id = "flow-1"
    flow._resolve_region_provider_ids = AsyncMock(return_value=True)

    result = await flow.async_step_init({})

    assert result["type"] == "form"
    assert result["step_id"] == "street_query"


async def test_house_step_updates_entry_and_schedules_reload():
    """House selection updates config entry and schedules reload."""
    entry = _build_entry()
    entry.options = {
        CONF_GROUP: "1.1",
        CONF_STREET_ID: 1,
        CONF_HOUSE_ID: 2,
        CONF_ADDRESS_NAME: "Old 1",
    }
    flow = StaleAddressRepairFlow(entry)
    flow.hass = MagicMock()
    flow.hass.config_entries = MagicMock()
    flow.handler = DOMAIN
    flow.flow_id = "flow-1"
    flow._region_id = 25
    flow._provider_id = 902
    flow._street_id = 1061
    flow._street_name = "Салютна"
    flow._house_options = {"26887": "2"}
    flow._api.fetch_group_by_address = AsyncMock(return_value="4.2")

    result = await flow.async_step_house({"house": "26887"})

    assert result["type"] == "create_entry"
    update_call = flow.hass.config_entries.async_update_entry.call_args
    updated_data = update_call.kwargs["data"]
    assert updated_data[CONF_STREET_ID] == 1061
    assert updated_data[CONF_HOUSE_ID] == 26887
    assert updated_data[CONF_ADDRESS_NAME] == "Салютна 2"
    assert updated_data[CONF_GROUP] is None
    updated_options = update_call.kwargs["options"]
    assert updated_options[CONF_STREET_ID] == 1061
    assert updated_options[CONF_HOUSE_ID] == 26887
    assert updated_options[CONF_ADDRESS_NAME] == "Салютна 2"
    assert updated_options[CONF_GROUP] is None
    flow.hass.config_entries.async_schedule_reload.assert_called_once_with(
        entry.entry_id
    )
