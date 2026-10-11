# AGENTS.md

Guidance for AI coding agents working in this repository. Keep changes minimal,
verify against the actual code, and follow the boundaries below.

## Project overview

Svitlo Yeah (Світло Є) is a [Home Assistant](https://www.home-assistant.io/)
custom integration (HACS) that tracks electricity-outage schedules from Ukrainian
energy providers. It exposes outage calendars, an `Electricity` status sensor,
"next outage / next connectivity" timestamp sensors, a force-refresh button, and
a `svitlo_yeah_data_changed` event. It supports many regions/providers (DTEK,
Yasno, Alerts Energy for Sumy, and community JSON feeds) with per-group configuration, all set
up through the Home Assistant UI. See `README.md` for the full region list and
entity reference.

This is a HACS integration, **not** a standalone Python library — the API classes
require a running Home Assistant instance (`hass`).

## Repository layout

- `custom_components/svitlo_yeah/` — the integration package (domain: `svitlo_yeah`).
  - `api/` — provider clients that fetch and parse raw outage data
    (`yasno.py`, `alerts_energy.py`, `dtek/`), plus `common_tools.py`.
  - `coordinator/` — `DataUpdateCoordinator` subclasses per provider that own
    fetch/refresh scheduling and expose events to the entities.
  - `entity.py`, `sensor.py`, `calendar.py`, `button.py` — HA entity platforms.
  - `config_flow.py` — UI setup/options flow.
  - `models/`, `const.py`, `manifest.json`, `translations/`, `icons.json`.
  - `quality_scale.yaml` — the status of each rule of the [integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/), in the format of Home Assistant core. hassfest skips this file for a custom integration, so no tool checks it. When a change makes a rule done, or breaks a done rule, change its status in the same commit.
  - `brand/` — the icon and the logo that Home Assistant and HACS show. They are copies of `icons/*.png`, which the README uses. If you change an image, change both copies: `tests/test_icons.py` makes sure that they are equal.
- `tests/` — pytest suite (`pytest-asyncio`, `freezegun`, `pytest-homeassistant-custom-component`).
  - `tests/e2e/` — e2e tests with real network access (see "Testing").
- `conftest.py` — loads the Home Assistant test plugin, also on Windows (see "Testing").
- `script/update_version.py` — bumps the version (see gotcha below).
- `justfile` — canonical task runner. `.ruff.toml`, `.pre-commit-config.yaml`,
  `pyproject.toml` — tooling config.

## Dev environment & commands

The project uses **[uv](https://docs.astral.sh/uv/)**. Run everything through
`uv run` so the project virtualenv is used. Do **not** `cd` into subdirectories
before running commands — run them from the repo root.

Use the `just` recipes. The `justfile` shows what each recipe runs.

- `just install`: after a clone, and after a change of the dependencies.
- `just upgrade`: when you upgrade all dependencies.
- `just lint`: after each code change.
- `just test`: after each change.
- `just test_e2e`: after a change of the code that reads a real source, and before a release. It needs network access.
- `just cov`: when you add or change tests, to see the lines of each module that no test runs. Keep each module above 95% (Silver rule `test-coverage`). The recipe fails when the total is below 95%, but it does not check each module, so read the table. `[tool.coverage.report]` in `pyproject.toml` excludes the same lines as Home Assistant core, for example `raise NotImplementedError`.
- `just pre`: before you finish a change.
- `just pre-update`: when you update the versions of the pre-commit hooks.
- `just version X.Y.Z`: when you change the version.

Run any ad-hoc Python via `uv run python ...`.

The pre-commit hooks also run the full test suite, so each commit runs it. They also run the `ty` type checker on the files of `[tool.ty.src]` in `pyproject.toml`, which is `custom_components` only, because the tests use mocks and wrong values on purpose. Fix a type error instead of adding a `ty:ignore` comment.

## Local test Home Assistant (optional)

You need a local Home Assistant only to see the integration work in a real Home Assistant. The test suite does not use it. An agent drives it through the [REST API](https://developers.home-assistant.io/docs/api/rest/) of Home Assistant, and drives the UI through Playwright MCP (see "UI checks with Playwright MCP").

To set it up:

1. Link `custom_components/svitlo_yeah` into the `custom_components` folder of the local Home Assistant configuration.
2. In the local Home Assistant, open your user profile, open the Security tab, and create a long-lived access token.
3. Put the token into the `.env` file in the repository root, on its own line: `HA_TEST_TOKEN=<token>`. Git ignores `.env`.

A script sends the token in the `Authorization: Bearer` header. For example, `POST /api/config/config_entries/flow` starts a config flow, and `GET /api/states/<entity_id>` gives the state of an entity. Read the token from `.env` inside the script, and never put the token on a command line or into output.

Home Assistant loads a code change only after a restart. If the local Home Assistant runs `python -m homeassistant` without a loop that starts it again, the `homeassistant.restart` service stops the server. In that case, ask the user to restart Home Assistant.

### UI checks with Playwright MCP (optional)

The Home Assistant frontend is built from Lit web components with open shadow roots. A browser tool that reads only the light DOM finds an empty page there. The [Playwright MCP](https://github.com/microsoft/playwright-mcp) server gives an accessibility snapshot that includes the shadow DOM, with a `ref` for each element. Thus an agent can walk a check scenario step by step, for example a config flow or a Reconfigure, and click and type by `ref`, without a script and without screenshots.

To set it up:

1. Add a stdio MCP server to your MCP client that runs `npx -y @playwright/mcp@latest --browser firefox --headless --user-data-dir <profile folder> --output-dir <output folder>`. Give both folders a place outside the repository where the server can write. Some MCP hubs start a server in a folder without write access, and then each call fails with `EPERM`.
2. If a call fails with `Browser "firefox" is not installed`, run `npx -y @playwright/mcp@latest install-browser firefox`. A new release of the package can need a new browser build.
3. Sign in to the local Home Assistant once. Start the same server without `--headless`, open `http://127.0.0.1:8123` in its window, and sign in yourself. The profile folder keeps the sign-in for the headless server. Do not let an agent type the password.

Keep `--headless` for the checks. A browser with a window draws no frames while the window is minimized or covered, and then each click waits until it times out. Two browsers cannot use one profile folder at the same time, so close the headless browser before you start the one with a window.

## Code style & conventions

- **Python 3.14+ only.** `requires-python = ">=3.14.2"` (tracking Home Assistant
  core), and ruff `target-version = "py314"`. You may freely use the newest idioms.
- **No `from __future__ import annotations`.** Annotations are deferred by default
  on 3.14; the import is redundant and must not be added.
- **Modern typing:** use PEP 604 unions (`str | None`) and PEP 585 builtins
  (`list[...]`, `dict[...]`) — not `Optional`, `Union`, `List`, `Dict`.
- **`TYPE_CHECKING` guards:** import types used only in annotations under
  `if TYPE_CHECKING:` (see `api/dtek/json.py`). Deferred annotations make this safe.
- **Ruff with `select = ALL`** and `max-complexity = 25`. The `ignore` list of `.ruff.toml` has only the rules that conflict with the formatter, `ANN401` and `CPY001`. The tests skip only the rules that a test has no reason to follow, and `.ruff.toml` gives the reason of each. A module in a subpackage imports a parent module by its absolute name, for example `from custom_components.svitlo_yeah.const import DOMAIN`, because `TID252` forbids `from ..const import DOMAIN`. A method that overrides a method of Home Assistant gets `@override` from `typing`, so that ruff does not report the arguments that it does not use. Prefer a narrowly-scoped `# noqa: RULE  # reason` over broadening the global ignores.
- **Timezone-aware datetimes everywhere.** This is an invariant: HA's
  `calendar.async_get_events` passes tz-aware datetimes, so
  `coordinator.get_events_between` and `api.get_events` datetimes are tz-aware
  too. Never introduce naive datetimes in production paths; parse to aware
  (usually via `homeassistant.util.dt`), and treat provider-local times as
  Europe/Kyiv. `DTZ*` ruff rules enforce this.
- **`# fmt: skip  # remove in 2027` on multi-line `except (...)` tuples**: these
  exist in `api/common_tools.py` to stop the formatter from
  reflowing the exception tuple onto one line. Keep the comment intact when you
  touch those lines; the marker signals it can be revisited in 2027.

## Testing

- A test with the `e2e` marker runs only with `just test_e2e`, not with `just test`.
- Put each test that needs real network access into `tests/e2e/`. `tests/e2e/conftest.py` adds the `e2e` marker to each test in that folder, so a test there needs no marker of its own.
- The tests run with [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component). It gives the fixtures of the Home Assistant core tests, for example `hass` and `aioclient_mock`. For a test that runs the config flow or sets up the integration, use the `hass` fixture.
- Put the shared entry data and the fake answers of the sources into `tests/helpers.py`, and the shared fixtures into `tests/conftest.py`. A test module never imports another test module. A module that sets up an entry or runs the config flow declares `pytestmark = pytest.mark.usefixtures("enable_custom_integrations", "empty_yasno_region_cache")`. These fixtures are not autouse in `tests/conftest.py`, because `enable_custom_integrations` needs the `hass` fixture, and each test would then start a Home Assistant.
- The plugin blocks sockets and DNS in each test. `tests/e2e/conftest.py` gives the tests in that folder the real network back.
- Home Assistant does not run on Windows, and the plugin does not load there on its own. The root `conftest.py` makes it load. Its docstring tells why `addopts` in `pyproject.toml` has `-p no:homeassistant`, and a comment in `pyproject.toml` tells why each test gets a new event loop. Read both before you change these settings.
- **Tests work around the code, not the reverse.** Do **not** compromise or add
  logic to production code merely to satisfy tests. When the test/non-production
  environment differs, absorb that difference inside the test code.
- Async tests use `asyncio_mode = "auto"` with a new event loop for each test; time is
  controlled with `freezegun`.

## Domain knowledge

### Providers & data sources

Outage data comes from several providers, each with its own `api/` client and `coordinator/`: Yasno, Alerts Energy for Sumy, and DTEK. DTEK and several oblasts are served by **JSON feeds** (community GitHub raw files) via `api/dtek/json.py`. All HTTP uses `aiohttp` through the session helpers of Home Assistant, and there is no bespoke HTTP stack. All current clients use the shared session of `async_get_clientsession(hass)`. Sumy uses only the public Alerts Energy hourly schedule endpoint, filtered to Sumyoblenergo; no login, emergency endpoint, possible-outage events or E-Svitlo fallback. See `README.md` for the authoritative region → provider → source table.

### Old states until new data

The entities must not become unavailable without need. Until a coordinator gets new data, the entities keep their old states. Thus a coordinator never raises `UpdateFailed` or `ConfigEntryNotReady` when a source does not answer, and a failed fetch keeps the last data. The Bronze rule `test-before-setup` of the integration quality scale conflicts with this requirement, because Home Assistant shows each entity of an entry that retries its setup as unavailable after a restart. The integration does not follow that rule on purpose. For the same reason, it does not follow the Silver rule `entity-unavailable`.

After each fetch, each coordinator calls `_set_last_fetch_failed`, which keeps `last_fetch_failed`. An outdated DTEK schedule is an answer, not a failure. The method writes one `info` line when the source stops answering, and one when it answers again (Silver rule `log-when-unavailable`). Thus the API clients log a failed request only at the debug level. The refresh button reads this flag and then raises a translated `HomeAssistantError`, so that the user sees the failure (Silver rule `action-exceptions`). The button never sets `last_update_success` to `False`, because that makes each entity of the entry unavailable.

Sumy has no authentication. Config entry migration from version 1.1 to 2.1 is local: take a concrete subgroup from the entry or consistent legacy Store group fields, remove account credentials, and close old reauthentication flows. Preserve entry/device/entity identifiers and user names. Missing or conflicting groups produce an Unknown state and a repair message pointing to Reconfigure, without deleting the entry. Existing accounts of the same subgroup stay separate; new duplicates are rejected.

The old states also stay across a restart. `IntegrationCoordinator` keeps the last data of the source in a `Store` with the key `svitlo_yeah.<entry_id>`. `_async_setup` loads it before the first fetch, `_async_store_last_data` saves it when it changed, and `async_remove_entry` in `__init__.py` deletes it. Each provider coordinator implements `_source_data` and `_restore_source_data`. DTEK keeps `fact` and `preset`, Yasno keeps the planned outages and the region of the entry, and Alerts Energy keeps a normalized dated Sumy snapshot with the configured group, completeness and source update time. A kept Yasno region only names the device: the client still asks the source for it. The kept answer about the group (`group_listed`) counts only when the kept group is the configured group, because a Reconfigure changes the group. Sumy converts legacy E-Svitlo cache locally with exact dates and boundaries, never using another subgroup's cache. A valid unknown day clears old intervals, while a failed request retains the last snapshot. Unknown/partial days do not claim normal electricity outside confirmed outages; expired dates never repeat on a new day.

### DTEK JSON freshness

`api/dtek/json.py` fetches JSON with a `fact` (and optional `preset`) structure and checks an `update` timestamp against `DTEK_FRESH_DATA_DAYS`. `fetch_data` returns a `FetchResult` enum — `FRESH`, `STALE`, or `UNAVAILABLE`. Newly fetched stale data is only adopted during setup with explicit user consent (`allow_stale_data=True`). At runtime, `STALE` leaves `self.data` as it is. Thus the coordinator keeps serving the last fresh copy, also after that copy is older than `DTEK_FRESH_DATA_DAYS`. The store of the entry keeps that copy across a restart (see «Old states until new data»). `test_stale_at_runtime_keeps_the_last_fresh_copy` pins this behavior. The `update` field uses `DD.MM.YYYY HH:MM` (or `HH:MM DD.MM.YYYY`).

### Hour-status grid (DTEK schedule encoding)

Per-day schedules are a map of hour-index → status string (parsed in
`api/dtek/base.py`). Status values:

- `"yes"` — no outage (ends any open outage).
- `"no"` — full-hour outage (continues an existing outage).
- `"second"` — outage in the **second** half hour (`hh:30`–`hh+1:00`); typically the
  **start** of a range.
- `"first"` — outage in the **first** half hour (`hh:00`–`hh:30`); typically the
  **end** of a range, and always closes at `hh:30`.
- Maybe/possible-outage variants also exist: `"maybe"`, `"msecond"`, `"mfirst"`
  (and `"?"`), handled alongside their definite counterparts.

`"first"`/`"second"` appear at range boundaries; `"no"`/`"maybe"` fill the interior.
Example: `13:"second", 14:"no", 15:"no", 16:"no", 17:"first"` → a single outage
range `12:30`–`16:30`. Consult `base.py` for the exact merging logic and the
`Scheduled` (may happen) vs `Planned` (will happen) distinction.

## Agent workflow & boundaries

- **Raise open questions before implementing.** If requirements are ambiguous or a
  change risks the invariants above, ask first.
- **Use a markdown checklist for multi-step work.** For any multi-stage
  implementation, write a checklist, tick items off as you complete them, and
  return the updated list.
- **Never touch git history or the index.** You are **not** allowed to run
  `git add`, `git commit`, `git rm`, or anything that stages or commits. Producing
  a diff or a commit message does not imply permission to commit.
- **Version-sync gotcha:** the version lives in **both** `pyproject.toml` (`version = "..."`) and `custom_components/svitlo_yeah/manifest.json` (`"version"`). They must match. Use `just version X.Y.Z` rather than editing either by hand.
