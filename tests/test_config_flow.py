"""Tests for config flow reconfigure behavior."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE

from custom_components.yasno_outages.config_flow import YasnoOutagesConfigFlow
from custom_components.yasno_outages.const import (
    CONF_ADDRESS_NAME,
    CONF_FILTER_PROBABLE,
    CONF_GROUP,
    CONF_HOUSE_ID,
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


async def test_reconfigure_updates_entry_not_creates_new(reconfigure_entry):
    """Reconfigure updates current entry and does not create new entry."""
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": SOURCE_RECONFIGURE}
    flow._is_reconfigure = True
    flow.data = {
        CONF_REGION: "Київ",
        CONF_PROVIDER: "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",
        CONF_GROUP: "1.1",
        CONF_FILTER_PROBABLE: False,
        CONF_STATUS_ALL_DAY_EVENTS: False,
    }
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    with patch.object(flow, "_get_reconfigure_entry", return_value=reconfigure_entry):
        result = await flow.async_step_preferences(user_input={})

    assert result["type"] == "abort"
    flow.async_update_reload_and_abort.assert_called_once()
    flow.async_create_entry.assert_not_called()
    assert flow.async_update_reload_and_abort.call_args.args[0] == reconfigure_entry


async def test_reconfigure_address_mode_replaces_group(reconfigure_entry):
    """Address reconfigure stores the newly validated group with its address."""
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": SOURCE_RECONFIGURE}
    flow._is_reconfigure = True
    flow.data = {
        CONF_REGION: "Київ",
        CONF_PROVIDER: "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",
        CONF_GROUP: "3.1",
    }
    flow._street_name = "Салютна"
    flow._house_name = "2"
    flow.data[CONF_STREET_ID] = 1061
    flow.data[CONF_HOUSE_ID] = 26887
    flow._house_options = {"26887": "2"}
    flow.api.get_region_by_name = MagicMock(return_value={"id": 25})
    flow.api.get_provider_by_name = MagicMock(return_value={"id": 902})
    flow.api.fetch_group_by_address = AsyncMock(return_value="1.1")
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})

    with patch.object(flow, "_get_reconfigure_entry", return_value=reconfigure_entry):
        await flow.async_step_address()
        assert CONF_GROUP not in flow.data
        await flow.async_step_house({"house": "26887"})
        await flow.async_step_preferences(
            user_input={
                CONF_FILTER_PROBABLE: True,
                CONF_STATUS_ALL_DAY_EVENTS: True,
            }
        )

    data = flow.async_update_reload_and_abort.call_args.kwargs["data"]
    assert data[CONF_GROUP] == "1.1"
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


@pytest.mark.parametrize("street_count", [1, 2])
async def test_complete_address_configuration(regions_data, street_count):
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": "user"}
    flow.api.regions_data = regions_data
    flow.api.fetch_regions = AsyncMock()
    flow.api.fetch_streets = AsyncMock(
        return_value=[
            {"id": 10 + index, "value": f"Test Street {index}"}
            for index in range(street_count)
        ]
    )
    flow.api.fetch_houses = AsyncMock(return_value=[{"id": 20, "value": "1"}])
    flow.api.fetch_group_by_address = AsyncMock(return_value="3.1")

    assert (await flow.async_step_user())["step_id"] == "user"
    assert (await flow.async_step_user({CONF_REGION: regions_data[0]["value"]}))[
        "step_id"
    ] == "method"
    assert (await flow.async_step_address())["step_id"] == "street_query"
    result = await flow.async_step_street_query({"street_query": "Test"})
    if street_count == 2:
        assert result["step_id"] == "street"
        result = await flow.async_step_street({"street": "10"})
    assert result["step_id"] == "house_query"
    assert (await flow.async_step_house_query({"house_query": "1"}))[
        "step_id"
    ] == "house"
    assert (await flow.async_step_house({"house": "20"}))["step_id"] == "preferences"
    result = await flow.async_step_preferences(
        {
            CONF_FILTER_PROBABLE: True,
            CONF_STATUS_ALL_DAY_EVENTS: False,
        }
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_GROUP] == "3.1"
    assert result["data"]["address_group"] == {
        "region_id": 25,
        "provider_id": 902,
        "street_id": 10,
        "house_id": 20,
        "group": "3.1",
    }
    assert result["data"][CONF_ADDRESS_NAME] == "Test Street 0 1"


async def test_complete_group_configuration_with_provider_selection(regions_data):
    flow = YasnoOutagesConfigFlow()
    flow.context = {"source": "user"}
    flow.api.regions_data = regions_data
    flow.api.fetch_regions = AsyncMock()
    flow.api.fetch_group_by_address = AsyncMock()
    region = regions_data[1]
    assert (await flow.async_step_user())["step_id"] == "user"
    assert (await flow.async_step_user({CONF_REGION: region["value"]}))[
        "step_id"
    ] == "provider"
    assert (await flow.async_step_provider({CONF_PROVIDER: region["dsos"][1]["name"]}))[
        "step_id"
    ] == "method"
    group_api = MagicMock()
    group_api.planned.fetch_planned_outages_data = AsyncMock()
    group_api.planned.get_groups.return_value = ["3.1", "4.2"]
    with patch(
        "custom_components.yasno_outages.config_flow.YasnoApi", return_value=group_api
    ):
        assert (await flow.async_step_group())["step_id"] == "group"
    assert (await flow.async_step_group({CONF_GROUP: "4.2"}))[
        "step_id"
    ] == "preferences"
    result = await flow.async_step_preferences(
        {
            CONF_FILTER_PROBABLE: True,
            CONF_STATUS_ALL_DAY_EVENTS: False,
        }
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_GROUP] == "4.2"
    assert CONF_STREET_ID not in result["data"]
    assert "address_group" not in result["data"]
    flow.api.fetch_group_by_address.assert_not_awaited()
