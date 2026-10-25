"""Regression tests for validated address groups and configuration transitions."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from custom_components.yasno_outages import async_setup_entry
from custom_components.yasno_outages.api import YasnoApiError, YasnoNotFoundError
from custom_components.yasno_outages.calendar import (
    YasnoPlannedOutagesCalendar,
    YasnoProbableOutagesCalendar,
)
from custom_components.yasno_outages.config_flow import YasnoOutagesConfigFlow
from custom_components.yasno_outages.const import DOMAIN
from custom_components.yasno_outages.repairs import StaleAddressRepairFlow
from custom_components.yasno_outages.sensor import SENSOR_TYPES, YasnoOutagesSensor

LOCATION_KEYS = {
    "region",
    "provider",
    "street_id",
    "house_id",
    "address_name",
    "group",
    "address_group",
}


@pytest.fixture
def entry():
    return MagicMock(
        entry_id="address-entry",
        domain=DOMAIN,
        title="Yasno Test Street 1",
        data={
            "region": "Test Region",
            "provider": "Test Provider",
            "street_id": 10,
            "house_id": 20,
            "address_name": "Test Street 1",
        },
        options={"scan_interval": 10, "filter_probable": False},
        update_listeners=[],
    )


@pytest.fixture
def setup_environment():
    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    def update_entry(entry, **changes):
        for key, value in changes.items():
            setattr(entry, key, value)

    hass.config_entries.async_update_entry.side_effect = update_entry
    api = MagicMock()
    api.fetch_regions = AsyncMock()
    api.get_region_by_name.return_value = {"id": 1}
    api.get_provider_by_name.return_value = {"id": 2}
    api.fetch_group_by_address = AsyncMock(return_value="1.1")
    api.planned.fetch_planned_outages_data = AsyncMock()
    api.planned.get_groups.return_value = ["1.1", "2.2"]

    def coordinator_factory(hass, entry, api, *, group):
        return MagicMock(
            hass=hass,
            config_entry=entry,
            api=api,
            group=group,
            async_config_entry_first_refresh=AsyncMock(),
        )

    with (
        patch("custom_components.yasno_outages.YasnoApi", return_value=api),
        patch(
            "custom_components.yasno_outages.YasnoOutagesCoordinator",
            side_effect=coordinator_factory,
        ),
        patch("custom_components.yasno_outages.async_check_and_create_repair"),
        patch("custom_components.yasno_outages.async_get_loaded_integration"),
        patch("custom_components.yasno_outages.repairs.ir.async_create_issue") as issue,
        patch(
            "custom_components.yasno_outages.repairs.ir.async_delete_issue"
        ) as delete,
    ):
        yield hass, api, issue, delete


def entity_unique_ids(entry):
    coordinator = entry.runtime_data.coordinator
    entities = [
        YasnoPlannedOutagesCalendar(coordinator),
        YasnoProbableOutagesCalendar(coordinator),
        *(YasnoOutagesSensor(coordinator, item) for item in SENSOR_TYPES),
    ]
    return [entity.unique_id for entity in entities]


async def test_address_resolution_persists_group(entry, setup_environment):
    hass, api, issue, delete = setup_environment
    assert await async_setup_entry(hass, entry)
    assert entry.data["group"] == "1.1"
    assert entry.data["address_group"] == {
        "region_id": 1,
        "provider_id": 2,
        "street_id": 10,
        "house_id": 20,
        "group": "1.1",
    }
    api.fetch_group_by_address.assert_awaited_once_with(
        region_id=1,
        provider_id=2,
        street_id=10,
        house_id=20,
    )
    issue.assert_not_called()
    delete.assert_called_once()


async def test_cached_group_keeps_validation_and_accepts_fresh_result(
    entry,
    setup_environment,
):
    hass, api, _, _ = setup_environment
    assert await async_setup_entry(hass, entry)
    api.fetch_group_by_address.return_value = "2.2"
    assert await async_setup_entry(hass, entry)
    assert api.fetch_group_by_address.await_count == 2
    assert entry.data["group"] == "2.2"
    assert entry.runtime_data.coordinator.group == "2.2"


async def test_stale_address_survives_restarts_and_recovers(entry, setup_environment):
    hass, api, issue, delete = setup_environment
    assert await async_setup_entry(hass, entry)
    original_ids = entity_unique_ids(entry)
    delete.reset_mock()
    api.fetch_group_by_address.side_effect = YasnoNotFoundError
    for _ in range(2):
        # Round trip persisted fields without retaining the old runtime object
        entry.data = json.loads(json.dumps(entry.data))
        entry.options = json.loads(json.dumps(entry.options))
        del entry.runtime_data
        assert await async_setup_entry(hass, entry)
        assert entry.runtime_data.coordinator.group == "1.1"
        assert entity_unique_ids(entry) == original_ids
        assert issue.call_args.kwargs["severity"] == ir.IssueSeverity.WARNING
        delete.assert_not_called()
    api.fetch_group_by_address.side_effect = None
    assert await async_setup_entry(hass, entry)
    delete.assert_called_once()
    assert api.fetch_group_by_address.await_count == 4


@pytest.mark.parametrize("group", [None, "", "1.1", "bogus"])
async def test_unvalidated_group_cannot_enable_fallback(
    entry,
    setup_environment,
    group,
):
    hass, api, issue, delete = setup_environment
    entry.data["group"] = group
    api.fetch_group_by_address.side_effect = YasnoNotFoundError
    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry)
    assert issue.call_args.kwargs["severity"] == ir.IssueSeverity.ERROR
    delete.assert_not_called()
    hass.config_entries.async_forward_entry_setups.assert_not_awaited()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("region", "Other Region"),
        ("provider", "Other Provider"),
        ("street_id", 11),
        ("house_id", 21),
        ("group", "2.2"),
        ("group", None),
    ],
)
async def test_options_cannot_reuse_cache_for_different_location(
    entry,
    setup_environment,
    key,
    value,
):
    hass, api, _, _ = setup_environment
    assert await async_setup_entry(hass, entry)
    entry.options[key] = value
    if key == "region":
        api.get_region_by_name.return_value = {"id": 3}
    if key == "provider":
        api.get_provider_by_name.return_value = {"id": 4}
    api.fetch_group_by_address.side_effect = YasnoNotFoundError
    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry)


async def test_removed_group_cannot_enable_fallback(entry, setup_environment):
    hass, api, _, delete = setup_environment
    assert await async_setup_entry(hass, entry)
    api.fetch_group_by_address.side_effect = YasnoNotFoundError
    api.planned.get_groups.return_value = ["2.2"]
    delete.reset_mock()
    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry)
    delete.assert_not_called()


@pytest.mark.parametrize("missing_key", ["street_id", "house_id"])
async def test_incomplete_address_cannot_use_cached_group(
    entry,
    setup_environment,
    missing_key,
):
    hass, _, _, _ = setup_environment
    assert await async_setup_entry(hass, entry)
    entry.data.pop(missing_key)
    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry)


async def test_empty_resolution_invalidates_previous_cache(entry, setup_environment):
    hass, api, _, _ = setup_environment
    assert await async_setup_entry(hass, entry)
    api.fetch_group_by_address.return_value = None
    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry)
    api.fetch_group_by_address.side_effect = YasnoNotFoundError
    with pytest.raises(ConfigEntryError):
        await async_setup_entry(hass, entry)


@pytest.mark.parametrize("endpoint", ["regions", "planned"])
async def test_other_endpoint_failures_are_not_address_failures(
    entry,
    setup_environment,
    endpoint,
):
    hass, api, issue, delete = setup_environment
    assert await async_setup_entry(hass, entry)
    delete.reset_mock()
    if endpoint == "regions":
        api.fetch_regions.side_effect = YasnoNotFoundError
    else:
        api.fetch_group_by_address.side_effect = YasnoNotFoundError
        api.planned.fetch_planned_outages_data.side_effect = YasnoApiError
    with pytest.raises(YasnoApiError):
        await async_setup_entry(hass, entry)
    delete.assert_not_called()
    if endpoint == "regions":
        issue.assert_not_called()


@pytest.mark.parametrize("error", [YasnoApiError, TimeoutError, ValueError])
async def test_unexpected_address_errors_do_not_use_cache(
    entry,
    setup_environment,
    error,
):
    hass, api, issue, delete = setup_environment
    assert await async_setup_entry(hass, entry)
    api.fetch_group_by_address.side_effect = error
    delete.reset_mock()
    with pytest.raises(error):
        await async_setup_entry(hass, entry)
    issue.assert_not_called()
    delete.assert_not_called()


async def test_group_configuration_uses_options_without_address_lookup(
    entry,
    setup_environment,
):
    hass, api, issue, _ = setup_environment
    entry.data = {"region": "Test Region", "provider": "Test Provider", "group": "1.1"}
    entry.options["group"] = "2.2"
    assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.coordinator.group == "2.2"
    api.fetch_group_by_address.assert_not_awaited()
    issue.assert_not_called()


async def test_success_normalizes_effective_location_options(entry, setup_environment):
    hass, api, _, _ = setup_environment
    entry.options.update({"street_id": 30, "house_id": 40, "group": None})
    assert await async_setup_entry(hass, entry)
    api.fetch_group_by_address.assert_awaited_once_with(
        region_id=1,
        provider_id=2,
        street_id=30,
        house_id=40,
    )
    assert entry.data["street_id"] == 30
    assert entry.data["house_id"] == 40
    assert entry.data["group"] == "1.1"
    assert not LOCATION_KEYS.intersection(entry.options)
    assert entry.options == {"scan_interval": 10, "filter_probable": False}


@pytest.mark.parametrize("stale", [False, True])
async def test_location_changed_during_lookup_is_not_overwritten(
    entry,
    setup_environment,
    stale,
):
    hass, api, _, _ = setup_environment
    assert await async_setup_entry(hass, entry)

    async def lookup(**_kwargs):
        # Simulate reconfiguration while the address HTTP request is pending
        entry.data = {
            "region": "New Region",
            "provider": "New Provider",
            "group": "2.2",
        }
        if stale:
            raise YasnoNotFoundError
        return "1.1"

    api.fetch_group_by_address.side_effect = lookup
    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, entry)
    assert entry.data == {
        "region": "New Region",
        "provider": "New Provider",
        "group": "2.2",
    }


async def test_location_changed_during_region_fetch_is_not_overwritten(
    entry,
    setup_environment,
):
    hass, api, _, _ = setup_environment

    async def fetch_regions():
        entry.data = {
            "region": "New Region",
            "provider": "New Provider",
            "street_id": 30,
            "house_id": 40,
        }

    api.fetch_regions.side_effect = fetch_regions
    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, entry)
    api.fetch_group_by_address.assert_not_awaited()
    assert "address_group" not in entry.data


def address_flow(entry):
    flow = YasnoOutagesConfigFlow()
    flow.data = dict(entry.data)
    flow.api.get_region_by_name = MagicMock(return_value={"id": 1})
    flow.api.get_provider_by_name = MagicMock(return_value={"id": 2})
    flow.api.fetch_group_by_address = AsyncMock(return_value="1.1")
    flow._street_name = "Test Street"
    flow._house_options = {"20": "1"}
    flow.async_create_entry = MagicMock(side_effect=lambda **values: values)
    return flow


async def test_new_address_flow_keeps_validated_group_and_address(entry):
    flow = address_flow(entry)
    await flow.async_step_house({"house": "20"})
    result = await flow.async_step_preferences(
        {"filter_probable": True, "status_all_day_events": True},
    )
    assert result["data"]["group"] == "1.1"
    assert result["data"]["street_id"] == 10
    assert result["data"]["address_group"]["house_id"] == 20
    assert result["title"] == "Yasno Test Region Test Street 1"


async def test_new_group_flow_keeps_only_group_location(entry):
    flow = address_flow(entry)
    await flow.async_step_group({"group": "2.2"})
    result = await flow.async_step_preferences(
        {"filter_probable": True, "status_all_day_events": True},
    )
    assert result["data"]["group"] == "2.2"
    assert "street_id" not in result["data"]
    assert "house_id" not in result["data"]
    assert "address_group" not in result["data"]
    assert result["title"] == "Yasno Test Region Test Provider 2.2"
    flow.api.fetch_group_by_address.assert_not_awaited()


@pytest.mark.parametrize("mode", ["group", "address"])
async def test_reconfigure_removes_legacy_location_options(
    entry,
    setup_environment,
    mode,
):
    hass, api, _, _ = setup_environment
    if mode == "address":
        entry.data = {
            "region": "Test Region",
            "provider": "Test Provider",
            "group": "2.2",
        }
    entry.options.update({**entry.data, "group": None})
    flow = address_flow(entry)
    flow.hass = hass
    flow.context = {"source": SOURCE_RECONFIGURE}
    flow._is_reconfigure = True

    def finish(config_entry, **changes):
        hass.config_entries.async_update_entry(config_entry, **changes)
        return {"type": "abort"}

    flow.async_update_reload_and_abort = MagicMock(side_effect=finish)
    with patch.object(flow, "_get_reconfigure_entry", return_value=entry):
        if mode == "group":
            await flow.async_step_group({"group": "1.1"})
        else:
            await flow.async_step_address()
            flow.data["street_id"] = 10
            await flow.async_step_house({"house": "20"})
        await flow.async_step_preferences(
            {"filter_probable": True, "status_all_day_events": True},
        )
    assert not LOCATION_KEYS.intersection(entry.options)
    assert entry.options["scan_interval"] == 10
    assert await async_setup_entry(hass, entry)
    assert entry.runtime_data.coordinator.group == "1.1"
    if mode == "group":
        api.fetch_group_by_address.assert_not_awaited()
        assert "street_id" not in entry.data
        assert "address_group" not in entry.data
    else:
        api.fetch_group_by_address.assert_awaited_once()
        assert entry.data["street_id"] == 10


async def test_repair_persists_new_group_and_survives_next_stale_response(
    entry,
    setup_environment,
):
    hass, api, issue, _ = setup_environment
    assert await async_setup_entry(hass, entry)
    original_ids = entity_unique_ids(entry)
    entry.options.update({"street_id": 10, "house_id": 20, "group": None})
    flow = StaleAddressRepairFlow(entry)
    flow.hass = hass
    flow.handler = DOMAIN
    flow.flow_id = "repair-flow"
    flow._region_id = 1
    flow._provider_id = 2
    flow._street_id = 30
    flow._street_name = "Test Street"
    flow._house_options = {"40": "1"}
    flow._api.fetch_group_by_address = AsyncMock(return_value="1.1")
    assert (await flow.async_step_house({"house": "40"}))["type"] == "create_entry"
    assert entry.data["group"] == "1.1"
    assert entry.data["address_group"]["house_id"] == 40
    assert not LOCATION_KEYS.intersection(entry.options)
    hass.config_entries.async_schedule_reload.assert_called_once_with(entry.entry_id)
    assert await async_setup_entry(hass, entry)
    api.fetch_group_by_address.assert_awaited_with(
        region_id=1,
        provider_id=2,
        street_id=30,
        house_id=40,
    )
    api.fetch_group_by_address.side_effect = YasnoNotFoundError
    assert await async_setup_entry(hass, entry)
    assert entity_unique_ids(entry) == original_ids
    assert issue.call_args.kwargs["severity"] == ir.IssueSeverity.WARNING


@pytest.mark.parametrize("result", [None, YasnoNotFoundError(), YasnoApiError()])
async def test_failed_repair_leaves_saved_location_unchanged(entry, result):
    original_data = dict(entry.data)
    original_options = dict(entry.options)
    flow = StaleAddressRepairFlow(entry)
    flow.hass = MagicMock()
    flow.handler = DOMAIN
    flow.flow_id = "repair-flow"
    flow._street_id = 30
    flow._house_options = {"40": "1"}
    flow._api.fetch_group_by_address = AsyncMock(return_value=result)
    if isinstance(result, Exception):
        flow._api.fetch_group_by_address.side_effect = result
    response = await flow.async_step_house({"house": "40"})
    assert response["type"] == "form"
    assert response["errors"]
    assert entry.data == original_data
    assert entry.options == original_options
    flow.hass.config_entries.async_update_entry.assert_not_called()
    flow.hass.config_entries.async_schedule_reload.assert_not_called()
