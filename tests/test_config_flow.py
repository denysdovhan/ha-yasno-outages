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


async def test_reconfigure_address_mode_clears_group(reconfigure_entry):
    """Address reconfigure clears group and stores address fields."""
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
    flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})

    with patch.object(flow, "_get_reconfigure_entry", return_value=reconfigure_entry):
        await flow.async_step_address()
        await flow.async_step_preferences(
            user_input={
                CONF_FILTER_PROBABLE: True,
                CONF_STATUS_ALL_DAY_EVENTS: True,
            }
        )

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
