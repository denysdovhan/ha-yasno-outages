"""Tests for integration setup logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from custom_components.yasno_outages import async_migrate_entry, async_setup_entry
from custom_components.yasno_outages.api import YasnoApiError, YasnoNotFoundError
from custom_components.yasno_outages.const import DOMAIN


@pytest.fixture
def hass():
    """Create a Home Assistant mock."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.flow.async_init = AsyncMock()

    def update_entry(entry, **changes):
        for key, value in changes.items():
            setattr(entry, key, value)

    hass.config_entries.async_update_entry.side_effect = update_entry
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
    entry.version = 3
    entry.minor_version = 0
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    entry.async_on_unload = MagicMock()
    entry.async_get_active_flows.return_value = []
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


@pytest.fixture
def setup_dependencies(regions_data):
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    with (
        patch(
            "custom_components.yasno_outages.api.base.BaseYasnoApi._get_data",
            AsyncMock(return_value=regions_data),
        ) as request,
        patch(
            "custom_components.yasno_outages.YasnoOutagesCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.yasno_outages.async_get_loaded_integration",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.yasno_outages.repairs.ir.async_create_issue"
        ) as create_issue,
        patch("custom_components.yasno_outages.repairs.ir.async_delete_issue"),
    ):
        yield request, create_issue


@pytest.mark.usefixtures("setup_dependencies")
@pytest.mark.parametrize(
    "provider_name",
    [
        "ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",
        "ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ",
        "АТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»",  # noqa: RUF001
    ],
)
async def test_setup_backfills_ids(hass, config_entry, regions_data, provider_name):
    config_entry.data["provider"] = provider_name
    config_entry.data["group"] = "15.1"

    assert await async_setup_entry(hass, config_entry) is True

    assert config_entry.data["region_id"] == 25
    assert config_entry.data["provider_id"] == 902
    assert config_entry.runtime_data.api.planned.region_id == 25
    assert config_entry.runtime_data.api.planned.provider_id == 902
    assert config_entry.runtime_data.api.planned.group == "15.1"
    assert config_entry.data["street_id"] == 1061
    assert "region" not in config_entry.data
    assert "provider" not in config_entry.data
    assert config_entry.version == 4
    assert config_entry.minor_version == 0

    regions_data[0]["dsos"][0]["name"] = "Renamed provider"
    assert await async_setup_entry(hass, config_entry) is True
    assert config_entry.runtime_data.api.planned.provider_id == 902


@pytest.mark.usefixtures("setup_dependencies")
async def test_setup_with_only_ids(hass, config_entry):
    config_entry.data = {"region_id": 25, "provider_id": 902, "group": "15.1"}
    config_entry.version = 4
    config_entry.minor_version = 0

    assert await async_setup_entry(hass, config_entry) is True
    assert config_entry.runtime_data.api.planned.provider_id == 902


@pytest.mark.usefixtures("setup_dependencies")
async def test_setup_migrates_legacy_options(hass, config_entry):
    config_entry.options = {
        "region": "Дніпро",
        "provider": "ЦЕК",
        "group": "1.1",
        "scan_interval": 5,
    }

    assert await async_setup_entry(hass, config_entry) is True
    assert config_entry.data["region_id"] == 3
    assert config_entry.data["provider_id"] == 303
    assert config_entry.data["group"] == "1.1"
    assert config_entry.options == {"scan_interval": 5}


async def test_setup_rejects_removed_id_without_name_fallback(
    hass, config_entry, setup_dependencies, regions_data
):
    config_entry.data.update({"region_id": 25, "provider_id": 999, "group": "15.1"})
    config_entry.data["provider"] = regions_data[0]["dsos"][0]["name"]

    with pytest.raises(ConfigEntryError, match="reconfigure"):
        await async_setup_entry(hass, config_entry)

    _, create_issue = setup_dependencies
    create_issue.assert_not_called()
    hass.config_entries.flow.async_init.assert_awaited_once_with(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
    )


@pytest.mark.parametrize("ids_in_options", [False, True])
@pytest.mark.usefixtures("setup_dependencies")
async def test_setup_survives_renamed_region_and_provider(
    hass, config_entry, regions_data, ids_in_options
):
    config_entry.data["group"] = "15.1"
    settings = config_entry.options if ids_in_options else config_entry.data
    settings.update({"region_id": 25, "provider_id": 902})
    regions_data[0]["value"] = "Київ (нова назва)"

    assert await async_setup_entry(hass, config_entry) is True

    assert config_entry.runtime_data.api.planned.region_id == 25
    assert config_entry.runtime_data.api.planned.provider_id == 902
    assert config_entry.runtime_data.api.planned.group == "15.1"


async def test_address_setup_uses_saved_ids_after_rename(
    hass, config_entry, setup_dependencies, regions_data
):
    config_entry.data.update({"region_id": 25, "provider_id": 902})
    request, _ = setup_dependencies
    request.side_effect = [regions_data, {"group": 1, "subgroup": 1}]

    assert await async_setup_entry(hass, config_entry) is True

    assert config_entry.runtime_data.api.planned.group == "1.1"
    assert request.call_args.kwargs["params"] == {
        "regionId": 25,
        "dsoId": 902,
        "streetId": 1061,
        "houseId": 26887,
    }


async def test_address_mode_resolves_group_each_setup(
    hass, config_entry, setup_dependencies, regions_data
):
    config_entry.data = {
        "region_id": 25,
        "provider_id": 902,
        "street_id": 1061,
        "house_id": 26887,
        "address_name": "Салютна 2",
    }
    request, _ = setup_dependencies
    request.side_effect = [
        regions_data,
        {"group": 1, "subgroup": 1},
        regions_data,
        {"group": 5, "subgroup": 2},
    ]

    assert await async_setup_entry(hass, config_entry) is True
    assert config_entry.runtime_data.api.planned.group == "1.1"
    assert await async_setup_entry(hass, config_entry) is True
    assert config_entry.runtime_data.api.planned.group == "5.2"
    assert "group" not in config_entry.data
    assert config_entry.data["address_name"] == "Салютна 2"
    assert config_entry.data["street_id"] == 1061
    assert config_entry.data["house_id"] == 26887


@pytest.mark.parametrize("error", [YasnoApiError("Server unavailable"), TimeoutError()])
async def test_setup_retries_regions_failure(
    hass, config_entry, setup_dependencies, error
):
    request, create_issue = setup_dependencies
    request.side_effect = error

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, config_entry)

    create_issue.assert_not_called()


@pytest.mark.parametrize("response", [{}, []])
async def test_setup_retries_invalid_regions_response(
    hass, config_entry, setup_dependencies, response
):
    request, create_issue = setup_dependencies
    request.return_value = response

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, config_entry)

    create_issue.assert_not_called()
    assert config_entry.version == 3


async def test_setup_missing_provider_requires_reconfigure(
    hass, config_entry, setup_dependencies
):
    config_entry.data["provider"] = "Removed provider"
    _, create_issue = setup_dependencies

    with pytest.raises(ConfigEntryError, match="reconfigure"):
        await async_setup_entry(hass, config_entry)

    create_issue.assert_not_called()
    hass.config_entries.flow.async_init.assert_awaited_once_with(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
    )


@pytest.mark.usefixtures("setup_dependencies")
async def test_setup_does_not_duplicate_reconfigure_flow(hass, config_entry):
    config_entry.data["provider"] = "Removed provider"
    config_entry.async_get_active_flows.return_value = [MagicMock()]

    with pytest.raises(ConfigEntryError, match="reconfigure"):
        await async_setup_entry(hass, config_entry)

    hass.config_entries.flow.async_init.assert_not_awaited()


@pytest.mark.usefixtures("setup_dependencies")
async def test_renamed_provider_migration_rejects_ambiguous_match(
    hass, config_entry, regions_data
):
    regions_data[0]["dsos"].append(
        {"id": 903, "name": regions_data[0]["dsos"][0]["name"]}
    )

    with pytest.raises(ConfigEntryError, match="reconfigure"):
        await async_setup_entry(hass, config_entry)

    assert config_entry.version == 3
    assert "provider_id" not in config_entry.data


@pytest.mark.parametrize("version", [1, 2, 3])
async def test_legacy_migration_resolves_names_during_setup(
    hass, config_entry, setup_dependencies, regions_data, version
):
    config_entry.version = version
    config_entry.minor_version = 1
    config_entry.data["provider"] = regions_data[0]["dsos"][0]["name"]
    config_entry.data["group"] = "15.1"
    config_entry.options = {"scan_interval": 5}
    if version == 1:
        config_entry.data["service"] = config_entry.data.pop("provider")

    request, _ = setup_dependencies
    assert await async_migrate_entry(hass, config_entry) is True
    request.assert_not_awaited()
    assert await async_setup_entry(hass, config_entry) is True
    assert config_entry.version == 4
    assert config_entry.minor_version == 0
    assert config_entry.data["region_id"] == 25
    assert config_entry.data["provider_id"] == 902
    assert "region" not in config_entry.data
    assert "provider" not in config_entry.data
    assert "service" not in config_entry.data
    assert config_entry.options == {"scan_interval": 5}
