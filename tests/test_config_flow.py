"""Tests for config flow reconfigure behavior."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE

from custom_components.yasno_outages.config_flow import (
    YasnoOutagesConfigFlow,
    YasnoOutagesOptionsFlow,
)
from custom_components.yasno_outages.const import (
    CONF_ADDRESS_NAME,
    CONF_FILTER_PROBABLE,
    CONF_GROUP,
    CONF_HOUSE_ID,
    CONF_PRESERVE_SCHEDULE,
    CONF_PROVIDER,
    CONF_REGION,
    CONF_STATUS_ALL_DAY_EVENTS,
    CONF_STREET_ID,
)


@pytest.fixture
def reconfigure_entry():
    """Create reconfigure config entry."""
    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.data = {
        CONF_REGION: "Київ",
        CONF_PROVIDER: "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",
        CONF_GROUP: "3.1",
    }
    entry.options = {
        CONF_FILTER_PROBABLE: True,
        CONF_STATUS_ALL_DAY_EVENTS: True,
    }
    return entry


async def test_options_flow_can_enable_and_disable_emergency_schedule(
    reconfigure_entry,
):
    with patch.object(YasnoOutagesOptionsFlow, "config_entry", reconfigure_entry):
        flow = YasnoOutagesOptionsFlow()
        form = await flow.async_step_init()
        assert form["data_schema"]({})[CONF_PRESERVE_SCHEDULE] is True

        disabled = form["data_schema"]({CONF_PRESERVE_SCHEDULE: False})
        result = await flow.async_step_init(disabled)
        assert result["data"][CONF_PRESERVE_SCHEDULE] is False

        reconfigure_entry.options = result["data"]
        flow = YasnoOutagesOptionsFlow()
        form = await flow.async_step_init()
        assert form["data_schema"]({})[CONF_PRESERVE_SCHEDULE] is False

        enabled = form["data_schema"]({CONF_PRESERVE_SCHEDULE: True})
        result = await flow.async_step_init(enabled)
        assert result["data"][CONF_PRESERVE_SCHEDULE] is True


async def test_reconfigure_starts_from_reconfigure_step(reconfigure_entry):
    """Reconfigure starts from dedicated reconfigure step."""
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": SOURCE_RECONFIGURE}
    flow.api.fetch_regions = AsyncMock()
    flow.api.regions_data = [{"value": "Київ", "id": 25, "dsos": []}]

    with patch.object(flow, "_get_reconfigure_entry", return_value=reconfigure_entry):
        result = await flow.async_step_reconfigure()

    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure"
    assert flow.data[CONF_REGION] == "Київ"


async def test_reconfigure_handles_regions_fetch_error(reconfigure_entry):
    """Reconfigure shows cannot_connect instead of raising on fetch failure."""
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": SOURCE_RECONFIGURE}
    flow.api.fetch_regions = AsyncMock(side_effect=Exception)
    flow.api.regions_data = []

    with patch.object(flow, "_get_reconfigure_entry", return_value=reconfigure_entry):
        result = await flow.async_step_reconfigure()

    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure"
    assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.parametrize(("region_id", "provider_id"), [(25, 902), (3, 303)])
async def test_region_and_provider_selectors_use_ids(
    regions_data, region_id, provider_id
):
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": "user"}
    flow.api.regions_data = regions_data
    flow.api.fetch_regions = AsyncMock()

    result = await flow.async_step_user()
    selection = {CONF_REGION: str(region_id)}
    assert result["data_schema"](selection) == selection
    result = await flow.async_step_user(selection)
    if result["step_id"] == "provider":
        selection = {CONF_PROVIDER: str(provider_id)}
        assert result["data_schema"](selection) == selection
        result = await flow.async_step_provider(selection)
    assert result["step_id"] == "method"
    assert flow.data["region_id"] == region_id
    assert flow.data["provider_id"] == provider_id

    await flow.async_step_group({CONF_GROUP: "15.1"})
    result = await flow.async_step_preferences(
        {
            CONF_FILTER_PROBABLE: True,
            CONF_STATUS_ALL_DAY_EVENTS: True,
            CONF_PRESERVE_SCHEDULE: True,
        }
    )
    assert result["data"]["region_id"] == region_id
    assert result["data"]["provider_id"] == provider_id
    assert result["data"][CONF_PRESERVE_SCHEDULE] is True
    assert CONF_REGION not in result["data"]
    assert CONF_PROVIDER not in result["data"]
    assert flow.api.get_region_by_id(region_id)["value"] in result["title"]


async def test_reconfigure_updates_entry_not_creates_new(
    reconfigure_entry, regions_data
):
    """Reconfigure updates current entry and does not create new entry."""
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": SOURCE_RECONFIGURE}
    flow._is_reconfigure = True
    flow.api.regions_data = regions_data
    flow.data = {
        "region_id": 25,
        "provider_id": 902,
        CONF_GROUP: "1.1",
    }
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    with patch.object(flow, "_get_reconfigure_entry", return_value=reconfigure_entry):
        form = await flow.async_step_preferences()
        result = await flow.async_step_preferences(form["data_schema"]({}))

    assert result["type"] == "abort"
    flow.async_update_reload_and_abort.assert_called_once()
    flow.async_create_entry.assert_not_called()
    assert flow.async_update_reload_and_abort.call_args.args[0] == reconfigure_entry


@pytest.mark.parametrize("mode", ["group", "address"])
async def test_new_entry_stores_region_provider_ids(regions_data, mode):
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": "user"}
    flow.api.regions_data = regions_data
    flow.data = {
        "region_id": 25,
        "provider_id": 902,
    }
    if mode == "group":
        flow.data[CONF_GROUP] = "15.1"
    else:
        flow.data.update({CONF_STREET_ID: 1061, CONF_HOUSE_ID: 26887})

    form = await flow.async_step_preferences()
    result = await flow.async_step_preferences(form["data_schema"]({}))

    assert result["data"]["region_id"] == 25
    assert result["data"]["provider_id"] == 902
    assert result["data"][CONF_PRESERVE_SCHEDULE] is True
    assert CONF_REGION not in result["data"]
    assert CONF_PROVIDER not in result["data"]


async def test_reconfigure_replaces_ids_and_legacy_options(
    reconfigure_entry, regions_data
):
    reconfigure_entry.data.update({"region_id": 25, "provider_id": 902})
    reconfigure_entry.options.update(
        {
            CONF_REGION: "Київ",
            CONF_PROVIDER: "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",
            "region_id": 25,
            "provider_id": 902,
            CONF_GROUP: None,
            CONF_STREET_ID: 1,
            CONF_HOUSE_ID: 2,
            CONF_ADDRESS_NAME: "Old address",
            CONF_PRESERVE_SCHEDULE: True,
        }
    )
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": SOURCE_RECONFIGURE}
    flow._is_reconfigure = True
    flow.api.regions_data = regions_data
    flow.data = {
        **reconfigure_entry.data,
        "region_id": 3,
        "provider_id": 303,
        CONF_GROUP: "1.1",
    }
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})

    with patch.object(flow, "_get_reconfigure_entry", return_value=reconfigure_entry):
        form = await flow.async_step_preferences()
        preferences = form["data_schema"]({CONF_PRESERVE_SCHEDULE: False})
        await flow.async_step_preferences(preferences)

    changes = flow.async_update_reload_and_abort.call_args.kwargs
    effective_config = {**changes["data"], **changes["options"]}
    assert effective_config["region_id"] == 3
    assert effective_config["provider_id"] == 303
    assert changes["data"][CONF_PRESERVE_SCHEDULE] is False
    assert changes["options"][CONF_PRESERVE_SCHEDULE] is False
    assert CONF_REGION not in effective_config
    assert CONF_PROVIDER not in effective_config
    assert effective_config[CONF_GROUP] == "1.1"
    assert CONF_STREET_ID not in effective_config
    assert CONF_HOUSE_ID not in effective_config


async def test_reconfigure_address_mode_clears_group(reconfigure_entry, regions_data):
    """Address reconfigure clears group and stores address fields."""
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": SOURCE_RECONFIGURE}
    flow._is_reconfigure = True
    flow.api.regions_data = regions_data
    flow.data = {
        "region_id": 25,
        "provider_id": 902,
        CONF_GROUP: "3.1",
    }
    flow._street_name = "Салютна"
    flow._house_name = "2"
    flow.data[CONF_STREET_ID] = 1061
    flow.data[CONF_HOUSE_ID] = 26887
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})

    with patch.object(flow, "_get_reconfigure_entry", return_value=reconfigure_entry):
        await flow.async_step_address()
        form = await flow.async_step_preferences()
        await flow.async_step_preferences(form["data_schema"]({}))

    data = flow.async_update_reload_and_abort.call_args.kwargs["data"]
    assert CONF_GROUP not in data
    assert data[CONF_STREET_ID] == 1061
    assert data[CONF_HOUSE_ID] == 26887
    assert data[CONF_ADDRESS_NAME] == "Салютна 2"


async def test_reconfigure_group_mode_clears_address_fields(reconfigure_entry):
    """Group reconfigure clears address fields."""
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": SOURCE_RECONFIGURE}
    flow._is_reconfigure = True
    flow.data = {
        CONF_REGION: "Київ",
        CONF_PROVIDER: "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",
        CONF_STREET_ID: 1061,
        CONF_HOUSE_ID: 26887,
        CONF_ADDRESS_NAME: "Салютна 2",
    }
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})

    with (
        patch.object(flow, "_get_reconfigure_entry", return_value=reconfigure_entry),
        patch.object(flow, "async_step_preferences", AsyncMock()),
    ):
        await flow.async_step_group(user_input={CONF_GROUP: "4.2"})

    assert flow.data[CONF_STREET_ID] is None
    assert flow.data[CONF_HOUSE_ID] is None
    assert flow.data[CONF_ADDRESS_NAME] is None
    assert flow.data[CONF_GROUP] == "4.2"
