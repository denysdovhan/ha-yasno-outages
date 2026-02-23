"""Tests for integration setup logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryError

from custom_components.yasno_outages import async_setup_entry
from custom_components.yasno_outages.api import YasnoNotFoundError
from custom_components.yasno_outages.const import DOMAIN


@pytest.fixture
def hass():
    """Create a Home Assistant mock."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    return hass


@pytest.fixture
def config_entry():
    """Create a config entry mock."""
    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.domain = DOMAIN
    entry.title = "Yasno Київ вул. Салютна 2"
    entry.data = {
        "region": "Київ",
        "provider": "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",
        "street_id": 1061,
        "house_id": 26887,
    }
    entry.options = {}
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    entry.async_on_unload = MagicMock()
    return entry


async def test_setup_fails_with_stale_address_issue(hass, config_entry):
    """Setup fails with ConfigEntryError when address ids are stale."""
    bootstrap_api = MagicMock()
    bootstrap_api.fetch_regions = AsyncMock()
    bootstrap_api.get_region_by_name = MagicMock(return_value={"id": 25})
    bootstrap_api.get_provider_by_name = MagicMock(return_value={"id": 902})
    bootstrap_api.fetch_group_by_address = AsyncMock(side_effect=YasnoNotFoundError)

    with (
        patch(
            "custom_components.yasno_outages.YasnoApi",
            return_value=bootstrap_api,
        ),
        patch(
            "custom_components.yasno_outages.async_check_and_create_repair",
            AsyncMock(),
        ),
        patch(
            "custom_components.yasno_outages.async_create_stale_address_issue",
            AsyncMock(),
        ) as create_issue,
        patch(
            "custom_components.yasno_outages.async_delete_stale_address_issue",
            AsyncMock(),
        ) as delete_issue,
        pytest.raises(ConfigEntryError),
    ):
        await async_setup_entry(hass, config_entry)

    create_issue.assert_called_once_with(hass, config_entry)
    delete_issue.assert_not_called()


async def test_setup_success_deletes_stale_address_issue(hass, config_entry):
    """Setup success clears stale-address issue."""
    bootstrap_api = MagicMock()
    bootstrap_api.fetch_regions = AsyncMock()
    bootstrap_api.get_region_by_name = MagicMock(return_value={"id": 25})
    bootstrap_api.get_provider_by_name = MagicMock(return_value={"id": 902})
    bootstrap_api.fetch_group_by_address = AsyncMock(return_value="1.1")

    entry_api = MagicMock()
    entry_api.fetch_regions = AsyncMock()

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()

    with (
        patch(
            "custom_components.yasno_outages.YasnoApi",
            side_effect=[bootstrap_api, entry_api],
        ),
        patch(
            "custom_components.yasno_outages.YasnoOutagesCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.yasno_outages.async_check_and_create_repair",
            AsyncMock(),
        ),
        patch(
            "custom_components.yasno_outages.async_create_stale_address_issue",
            AsyncMock(),
        ) as create_issue,
        patch(
            "custom_components.yasno_outages.async_delete_stale_address_issue",
            AsyncMock(),
        ) as delete_issue,
        patch(
            "custom_components.yasno_outages.async_get_loaded_integration",
            return_value=MagicMock(),
        ),
    ):
        result = await async_setup_entry(hass, config_entry)

    assert result is True
    create_issue.assert_not_called()
    delete_issue.assert_called_once_with(hass, config_entry)
