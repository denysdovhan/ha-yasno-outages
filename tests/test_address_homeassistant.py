"""Address lifecycle checks against the Home Assistant version in pyproject.toml.

Private state and storage helpers prepare isolated entries and flush delayed saves.
The lifecycle fixture uses public setup, unload and reload methods to test locking.
Recheck these fixtures when upgrading Home Assistant; HTTP and platforms are mocked.
"""

import asyncio
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.repairs.issue_handler import RepairsFlowManager
from homeassistant.components.repairs.websocket_api import ws_list_issues
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import frame
from homeassistant.helpers import issue_registry as ir

from custom_components import yasno_outages
from custom_components.yasno_outages import async_setup_entry, config_flow
from custom_components.yasno_outages.api import (
    PlannedOutagesApi,
    YasnoApi,
    YasnoApiError,
    YasnoNotFoundError,
)
from custom_components.yasno_outages.api.const import (
    GROUP_BY_ADDRESS_ENDPOINT,
    HOUSES_ENDPOINT,
    PLANNED_OUTAGES_ENDPOINT,
    PROBABLE_OUTAGES_ENDPOINT,
    REGIONS_ENDPOINT,
    STREETS_ENDPOINT,
)
from custom_components.yasno_outages.calendar import (
    YasnoPlannedOutagesCalendar,
    YasnoProbableOutagesCalendar,
)
from custom_components.yasno_outages.const import DOMAIN
from custom_components.yasno_outages.coordinator import YasnoOutagesCoordinator
from custom_components.yasno_outages.repairs import StaleAddressRepairFlow
from custom_components.yasno_outages.sensor import SENSOR_TYPES, YasnoOutagesSensor


@pytest.fixture
async def runtime(tmp_path, regions_data, planned_outage_data, probable_outage_data):
    hass = HomeAssistant(str(tmp_path))
    loop_errors = []
    original_handler = hass.loop.get_exception_handler()
    hass.loop.set_exception_handler(lambda _loop, context: loop_errors.append(context))
    frame.async_setup(hass)
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    dr.async_setup(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    await ir.async_load(hass)
    region = regions_data[0]
    entry = ConfigEntry(
        data={
            "region": region["value"],
            "provider": region["dsos"][0]["name"],
            "street_id": 10,
            "house_id": 20,
        },
        options={},
        domain=DOMAIN,
        title="Test address",
        source="user",
        version=3,
        minor_version=0,
        unique_id=None,
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )
    with patch.object(hass.config_entries, "async_setup", return_value=True):
        await hass.config_entries.async_add(entry)

    address_response = AsyncMock(return_value={"group": 3, "subgroup": 1})

    async def response(_session, url, **kwargs):
        if url == GROUP_BY_ADDRESS_ENDPOINT:
            return await address_response(**kwargs)
        return {
            REGIONS_ENDPOINT: regions_data,
            STREETS_ENDPOINT: [
                {"id": 30, "value": "Test Street"},
                {"id": 31, "value": "Another Street"},
            ],
            HOUSES_ENDPOINT: [{"id": 40, "value": "1"}],
            PLANNED_OUTAGES_ENDPOINT.format(
                region_id=25, dso_id=902
            ): planned_outage_data,
            PROBABLE_OUTAGES_ENDPOINT: probable_outage_data,
        }[url]

    with (
        patch(
            "custom_components.yasno_outages.api.base.BaseYasnoApi._get_data",
            side_effect=response,
        ),
        patch(
            "custom_components.yasno_outages.coordinator.YasnoOutagesCoordinator.async_fetch_translations"
        ),
        patch("custom_components.yasno_outages.async_get_loaded_integration"),
        patch.object(ConfigEntries, "async_forward_entry_setups"),
    ):
        yield hass, entry, address_response
    await entry._async_process_on_unload(hass)
    await hass.async_stop()
    hass.loop.set_exception_handler(original_handler)
    assert not loop_errors


@pytest.fixture
async def lifecycle_runtime(runtime):
    hass, entry, address_response = runtime
    integration = SimpleNamespace(
        domain=DOMAIN,
        logger=yasno_outages.LOGGER,
        async_get_component=AsyncMock(return_value=yasno_outages),
        async_get_platform=AsyncMock(return_value=config_flow),
    )
    hass.config.components.add(DOMAIN)
    with (
        patch("homeassistant.loader.async_get_integration", return_value=integration),
        patch("homeassistant.config_entries.support_entry_unload", return_value=True),
        patch(
            "homeassistant.config_entries.support_remove_from_device",
            return_value=False,
        ),
        patch.object(ConfigEntries, "async_unload_platforms", return_value=True),
    ):
        yield hass, entry, address_response
        await hass.config_entries.async_unload(entry.entry_id)


def register_entities(hass, entry):
    coordinator = entry.runtime_data.coordinator
    entities = [
        ("calendar", YasnoPlannedOutagesCalendar(coordinator)),
        ("calendar", YasnoProbableOutagesCalendar(coordinator)),
        *(("sensor", YasnoOutagesSensor(coordinator, item)) for item in SENSOR_TYPES),
    ]
    registry = er.async_get(hass)
    return [
        registry.async_get_or_create(
            domain,
            DOMAIN,
            entity.unique_id,
            config_entry=entry,
        ).entity_id
        for domain, entity in entities
    ]


async def setup_entry(hass, entry):
    entry._async_set_state(hass, ConfigEntryState.SETUP_IN_PROGRESS, None)
    result = await async_setup_entry(hass, entry)
    entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    return result


def repair_flow(hass, entry):
    flow = StaleAddressRepairFlow(entry)
    flow.hass = hass
    flow.handler = DOMAIN
    flow.flow_id = "repair"
    flow._region_id = 25
    flow._provider_id = 902
    flow._street_id = 30
    flow._street_name = "Test Street"
    flow._house_options = {"40": "1"}
    return flow


async def test_real_storage_reload_preserves_entities_and_warning(runtime):
    hass, entry, address_response = runtime
    with patch.object(hass.config_entries, "async_reload") as reload_entry:
        assert await setup_entry(hass, entry)
        entity_ids = register_entities(hass, entry)
        renamed = er.async_get(hass).async_update_entity(
            entity_ids[0],
            new_entity_id="calendar.household_outages",
        )
        entity_ids[0] = renamed.entity_id
        await hass.async_block_till_done()
        reload_entry.assert_not_called()
        await entry._async_process_on_unload(hass)
        await hass.config_entries._store.async_save(hass.config_entries._data_to_save())

        # Read the entry back through Home Assistant's own storage implementation
        hass.config_entries = ConfigEntries(hass, {})
        await hass.config_entries.async_initialize()
        restored_entry = hass.config_entries.async_get_entry(entry.entry_id)
        assert restored_entry is not entry
        assert restored_entry.data["group"] == "3.1"
        address_response.side_effect = YasnoNotFoundError
        issue_id = f"stale_address_ids_{entry.entry_id}"
        for _ in range(2):
            assert await setup_entry(hass, restored_entry)
            assert register_entities(hass, restored_entry) == entity_ids
            issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
            assert issue.severity == ir.IssueSeverity.WARNING
            assert restored_entry.runtime_data.api.planned.get_planned_outages_data()
            await restored_entry._async_process_on_unload(hass)
        address_response.side_effect = None
        assert await setup_entry(hass, restored_entry)
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
        await restored_entry._async_process_on_unload(hass)


@pytest.mark.parametrize(
    ("mode", "address_found"),
    [("group", False), ("address", True), ("address", False)],
)
async def test_legacy_reconfigure_survives_storage(runtime, mode, address_found):
    hass, entry, address_response = runtime
    preferences = {
        "scan_interval": 10,
        "filter_probable": False,
        "status_all_day_events": False,
    }
    location = (
        {"group": "3.1"}
        if mode == "group"
        else {"street_id": 31, "house_id": 40, "address_name": "Another Street 1"}
    )
    # Produced by 2687549's repair followed by reconfigure to either mode
    hass.config_entries.async_update_entry(
        entry,
        data={
            "region": entry.data["region"],
            "provider": entry.data["provider"],
            "filter_probable": False,
            "status_all_day_events": False,
            **location,
        },
        options={
            **preferences,
            "street_id": 30,
            "house_id": 40,
            "address_name": "Test Street 1",
            "group": None,
        },
    )

    async def lookup(**kwargs):
        if address_found and kwargs["params"]["streetId"] == 31:
            return {"group": 3, "subgroup": 1}
        raise YasnoNotFoundError

    address_response.side_effect = lookup
    for _ in range(2):
        await hass.config_entries._store.async_save(hass.config_entries._data_to_save())
        hass.config_entries = ConfigEntries(hass, {})
        await hass.config_entries.async_initialize()
        restored = hass.config_entries.async_get_entry(entry.entry_id)
        address_response.reset_mock()
        if mode == "address" and not address_found:
            with pytest.raises(ConfigEntryError):
                await setup_entry(hass, restored)
            assert restored.data.get("address_group") is None
            assert restored.data.get("group") is None
        else:
            assert await setup_entry(hass, restored)
            assert restored.runtime_data.coordinator.group == "3.1"
        assert restored.options == preferences
        if mode == "group":
            address_response.assert_not_awaited()
            assert restored.data.get("address_group") is None
        else:
            address_response.assert_awaited_once_with(
                params={"regionId": 25, "dsoId": 902, "streetId": 31, "houseId": 40}
            )
            if address_found:
                assert restored.data["address_group"] == {
                    "region_id": 25,
                    "provider_id": 902,
                    "street_id": 31,
                    "house_id": 40,
                    "group": "3.1",
                }
        await restored._async_process_on_unload(hass)


async def test_ignored_repair_survives_storage_until_successful_revalidation(
    lifecycle_runtime,
):
    hass, entry, address_response = lifecycle_runtime
    assert await hass.config_entries.async_setup(entry.entry_id)
    address_response.side_effect = YasnoNotFoundError
    assert await hass.config_entries.async_reload(entry.entry_id)
    registry = ir.async_get(hass)
    issue_id = f"stale_address_ids_{entry.entry_id}"
    assert (
        registry.async_get_issue(DOMAIN, issue_id).severity == ir.IssueSeverity.WARNING
    )
    ir.async_ignore_issue(hass, DOMAIN, issue_id, ignore=True)
    dismissed_version = registry.async_get_issue(DOMAIN, issue_id).dismissed_version
    assert dismissed_version is not None

    for _ in range(2):
        assert await hass.config_entries.async_reload(entry.entry_id)
        issue = registry.async_get_issue(DOMAIN, issue_id)
        assert issue.active
        assert issue.dismissed_version == dismissed_version

    assert await hass.config_entries.async_unload(entry.entry_id)
    await registry._store.async_save(registry._data_to_save())
    await registry.async_load()
    restored_issue = registry.async_get_issue(DOMAIN, issue_id)
    assert not restored_issue.active
    assert restored_issue.dismissed_version == dismissed_version
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert (
        registry.async_get_issue(DOMAIN, issue_id).dismissed_version
        == dismissed_version
    )

    # An unusable cache stops setup even if the earlier warning was ignored
    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "address_group": None}
    )
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue.severity == ir.IssueSeverity.ERROR
    assert issue.dismissed_version == dismissed_version
    connection = MagicMock()
    ws_list_issues(hass, connection, {"id": 1, "type": "repairs/list_issues"})
    listed = connection.send_result.call_args.args[1]["issues"]
    assert len(listed) == 1
    assert listed[0]["ignored"] is True
    assert listed[0]["severity"] == ir.IssueSeverity.ERROR

    address_response.side_effect = None
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert registry.async_get_issue(DOMAIN, issue_id) is None
    await registry._store.async_save(registry._data_to_save())
    await registry.async_load()
    assert registry.async_get_issue(DOMAIN, issue_id) is None

    address_response.side_effect = YasnoNotFoundError
    assert await hass.config_entries.async_reload(entry.entry_id)
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue.active
    assert issue.severity == ir.IssueSeverity.WARNING
    assert issue.dismissed_version is None
    ws_list_issues(hass, connection, {"id": 2, "type": "repairs/list_issues"})
    assert connection.send_result.call_args.args[1]["issues"][0]["ignored"] is False


@pytest.mark.parametrize("changed", [True, False])
async def test_loaded_repair_triggers_one_reload(runtime, changed):
    hass, entry, _ = runtime
    assert await setup_entry(hass, entry)
    flow = repair_flow(hass, entry)
    if not changed:
        await entry._async_process_on_unload(hass)
        with patch.object(hass.config_entries, "async_reload"):
            await flow.async_step_house({"house": "40"})
            await hass.async_block_till_done()
        assert await setup_entry(hass, entry)
        flow = repair_flow(hass, entry)
        flow.flow_id = "second-repair"
    with patch.object(hass.config_entries, "async_reload") as reload_entry:
        await flow.async_step_house({"house": "40"})
        await hass.async_block_till_done()
        reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_repair_does_not_overwrite_concurrent_reconfiguration(runtime):
    hass, entry, _ = runtime
    flow = repair_flow(hass, entry)
    replacement = {
        "region": "Other Region",
        "provider": "Other Provider",
        "group": "2.2",
    }
    hass.config_entries.async_update_entry(entry, data=replacement)
    response = await flow.async_step_house({"house": "40"})
    assert response["type"] == "abort"
    assert response["reason"] == "configuration_changed"
    assert entry.data == replacement


async def test_fallback_checks_group_after_coordinator_refresh(runtime):
    hass, entry, address_response = runtime
    assert await setup_entry(hass, entry)
    schedule = entry.runtime_data.api.planned.planned_outages_data
    await entry._async_process_on_unload(hass)
    address_response.side_effect = YasnoNotFoundError
    requests = 0

    async def fetch(api):
        nonlocal requests
        requests += 1
        api.planned_outages_data = schedule if requests == 1 else {}

    with (
        patch.object(PlannedOutagesApi, "fetch_planned_outages_data", fetch),
        patch.object(ConfigEntries, "async_forward_entry_setups") as forward,
        pytest.raises(ConfigEntryError),
    ):
        await setup_entry(hass, entry)
    forward.assert_not_awaited()


async def test_complete_repair_failure_recovery_and_reload(runtime):
    hass, entry, address_response = runtime
    assert await setup_entry(hass, entry)
    entity_ids = register_entities(hass, entry)
    await entry._async_process_on_unload(hass)
    address_response.side_effect = YasnoNotFoundError
    assert await setup_entry(hass, entry)
    issue_id = f"stale_address_ids_{entry.entry_id}"
    registry = ir.async_get(hass)
    assert (
        registry.async_get_issue(DOMAIN, issue_id).severity == ir.IssueSeverity.WARNING
    )

    flow = StaleAddressRepairFlow(entry)
    flow.hass = hass
    flow.handler = DOMAIN
    flow.flow_id = "repair"
    flow.init_data = {"issue_id": issue_id}
    assert (await flow.async_step_init())["step_id"] == "street_query"
    assert (await flow.async_step_street_query({"street_query": "Test"}))[
        "step_id"
    ] == "street"
    assert (await flow.async_step_street({"street": "30"}))["step_id"] == "house_query"
    assert (await flow.async_step_house_query({"house_query": "1"}))[
        "step_id"
    ] == "house"
    result = await flow.async_step_house({"house": "40"})
    assert result["errors"] == {"base": "cannot_connect"}
    assert registry.async_get_issue(DOMAIN, issue_id) is not None
    assert entry.data["house_id"] == 20

    address_response.side_effect = None
    with patch.object(hass.config_entries, "async_reload") as reload_entry:
        result = await flow.async_step_house({"house": "40"})
        assert result["type"] == "create_entry"
        await RepairsFlowManager(hass).async_finish_flow(flow, result)
        await hass.async_block_till_done()
        reload_entry.assert_awaited_once_with(entry.entry_id)
    assert registry.async_get_issue(DOMAIN, issue_id) is None
    assert entry.data["address_group"]["house_id"] == 40
    await entry._async_process_on_unload(hass)
    assert await setup_entry(hass, entry)
    assert register_entities(hass, entry) == entity_ids
    assert registry.async_get_issue(DOMAIN, issue_id) is None


@pytest.mark.parametrize(
    ("mode", "phase", "replacement_fails"),
    [
        ("address", "regions", False),
        ("address", "refresh", False),
        ("group", "regions", False),
        ("group", "refresh", False),
        ("fallback", "regions", False),
        ("fallback", "planned", False),
        ("fallback", "refresh", False),
        ("fallback", "refresh", True),
    ],
)
async def test_reconfiguration_during_setup_never_forwards_old_group(
    lifecycle_runtime, mode, phase, replacement_fails
):
    hass, entry, address_response = lifecycle_runtime
    if mode == "group":
        hass.config_entries.async_update_entry(
            entry,
            data={
                "region": entry.data["region"],
                "provider": entry.data["provider"],
                "group": "3.1",
            },
        )
    elif mode == "fallback":
        assert await hass.config_entries.async_setup(entry.entry_id)
        assert await hass.config_entries.async_unload(entry.entry_id)
        address_response.side_effect = YasnoNotFoundError

    target, method = {
        "regions": (YasnoApi, "fetch_regions"),
        "planned": (PlannedOutagesApi, "fetch_planned_outages_data"),
        "refresh": (YasnoOutagesCoordinator, "async_config_entry_first_refresh"),
    }[phase]
    original = getattr(target, method)
    pending = asyncio.Event()
    resume = asyncio.Event()

    async def pause(instance):
        if replacement_fails and pending.is_set():
            raise YasnoApiError
        await original(instance)
        if not pending.is_set() and (
            phase != "regions" or instance.planned.group is not None
        ):
            pending.set()
            await resume.wait()

    forwarded_groups = []

    async def forward(_entry, _platforms):
        forwarded_groups.append(_entry.runtime_data.coordinator.group)

    with (
        patch.object(target, method, pause),
        patch.object(ConfigEntries, "async_forward_entry_setups", side_effect=forward),
    ):
        setup = hass.async_create_task(hass.config_entries.async_setup(entry.entry_id))
        async with asyncio.timeout(5):
            await pending.wait()
        assert entry.setup_lock.locked()
        replacement = {
            "region": entry.data["region"],
            "provider": entry.data["provider"],
            "group": "4.1",
        }
        hass.config_entries.async_update_entry(entry, data=replacement)
        reload_task = hass.async_create_task(
            hass.config_entries.async_reload(entry.entry_id)
        )
        assert not setup.done()
        assert not reload_task.done()
        resume.set()
        assert not await setup
        assert await reload_task is not replacement_fails
    assert forwarded_groups == ([] if replacement_fails else ["4.1"])
    assert entry.state is (
        ConfigEntryState.SETUP_ERROR if replacement_fails else ConfigEntryState.LOADED
    )
    assert entry.data == replacement
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, f"stale_address_ids_{entry.entry_id}"
        )
        is None
    )


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("replacement_fails", [False, True])
async def test_superseded_address_404_does_not_create_repair(
    lifecycle_runtime, cached, replacement_fails
):
    hass, entry, address_response = lifecycle_runtime
    if cached:
        assert await hass.config_entries.async_setup(entry.entry_id)
        assert await hass.config_entries.async_unload(entry.entry_id)

    pending = asyncio.Event()
    resume = asyncio.Event()

    async def stale(**_kwargs):
        pending.set()
        await resume.wait()
        raise YasnoNotFoundError

    address_response.side_effect = stale
    setup = hass.async_create_task(hass.config_entries.async_setup(entry.entry_id))
    async with asyncio.timeout(5):
        await pending.wait()
    hass.config_entries.async_update_entry(
        entry,
        data={
            "region": entry.data["region"],
            "provider": entry.data["provider"],
            "group": "4.1",
        },
    )
    resume.set()
    assert not await setup
    registry = ir.async_get(hass)
    issue_id = f"stale_address_ids_{entry.entry_id}"
    issue_before_reload = registry.async_get_issue(DOMAIN, issue_id)
    if replacement_fails:
        with patch.object(YasnoApi, "fetch_regions", side_effect=YasnoApiError):
            assert not await hass.config_entries.async_reload(entry.entry_id)
    else:
        assert await hass.config_entries.async_reload(entry.entry_id)
    assert registry.async_get_issue(DOMAIN, issue_id) is None
    assert issue_before_reload is None


@pytest.mark.parametrize("failed_request", [1, 2])
async def test_fallback_schedule_failure_uses_only_current_setup_data(
    lifecycle_runtime, planned_outage_data, failed_request, caplog
):
    hass, entry, address_response = lifecycle_runtime
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert await hass.config_entries.async_unload(entry.entry_id)
    address_response.side_effect = YasnoNotFoundError
    requests = 0

    async def fetch(api):
        nonlocal requests
        requests += 1
        if requests == failed_request:
            raise YasnoApiError
        api.planned_outages_data = planned_outage_data

    with (
        patch.object(PlannedOutagesApi, "fetch_planned_outages_data", fetch),
        patch.object(ConfigEntries, "async_forward_entry_setups") as forward,
    ):
        result = await hass.config_entries.async_setup(entry.entry_id)
    assert requests == failed_request
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, f"stale_address_ids_{entry.entry_id}"
    )
    if failed_request == 1:
        assert not result
        assert entry.state is ConfigEntryState.SETUP_ERROR
        forward.assert_not_awaited()
        assert issue.severity == ir.IssueSeverity.ERROR
    else:
        assert result
        assert (
            entry.runtime_data.api.planned.planned_outages_data == planned_outage_data
        )
        assert entry.runtime_data.api.planned.get_planned_outages_data()
        assert "Failed to fetch planned outages, using cached data" in caplog.text
        forward.assert_awaited_once()
        assert issue.severity == ir.IssueSeverity.WARNING
