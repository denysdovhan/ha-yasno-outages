# AI Coding Agents Guide

## Purpose

Agents act as senior Python collaborators. Keep responses concise,
clarify uncertainty before coding, and align suggestions with the rules linked below.

## Project Overview

This repository is a Home Assistant custom integration providing electricity outage schedules for Ukraine using the [Yasno API](https://yasno.ua). Main codebase lives under `custom_components/yasno_outages`.

### Code structure

- `translations/` - folder containing translations (en.json, uk.json).
- `__init__.py` - init file of the integration, creates entries, sets up platforms, handles entry reload/unload. Stores coordinator in `entry.runtime_data`.
- `api.py` - a file containing an API class for fetching data. Should be Home Assistant agnostic, since in the future it's planned to move it to the separate package. Uses `aiohttp` for async HTTP requests.
- `config_flow.py` - a file describing a flow to create new entries and options flow for reconfiguration. Multi-step flow: region → service (DSO) → group.
- `const.py` - a file containing constants used throughout the project. Use `homeassistant.const` for commonly used constants.
- `coordinator.py` - a data fetching coordinator (`DataUpdateCoordinator`). Fetches data from the API, transforms it to the proper format, and passes them to sensors and calendar entities. Polls API every 15 minutes.
- `entity.py` - a base entity class (`YasnoOutagesEntity`) that is used as a template when creating sensors and calendar. Contains important `DeviceInfo` joining different entities into a single device.
- `repairs.py` - repair flow for detecting and notifying users about deprecated configuration (API v1 → v2 migration).
- `manifest.json` - a file declaring an integration manifest.
- `sensor.py` - declares sensors using entity descriptors. Implements five sensors: electricity state (enum), schedule updated timestamp, next outage, next possible outage, next connectivity.
- `calendar.py` - implements calendar entity showing outage events in a timeline format.

<instruction>Fill in by LLM assistant memory</instruction>

### Using Coordinator to Fetch Data

We use a single `DataUpdateCoordinator` per config entry that polls the Yasno API every 15 minutes. The coordinator is created in `__init__.py` during setup and stored directly in `entry.runtime_data`. Platforms (sensors, calendar) retrieve the coordinator from `config_entry.runtime_data`.

The coordinator:

- Resolves region/service names to IDs on first refresh
- Fetches outage schedules for the configured region, service (DSO), and group
- Transforms API data into `CalendarEvent` objects
- Computes derived values (current state, next outage times, etc.)

Documentation: https://developers.home-assistant.io/docs/integration_fetching_data

### Decouple API Data from Coordinator

Coordinator should not rely on API response structure. Instead, transform data into plain Python objects (e.g., dataclasses) on API class level, so coordinator only calls API methods and works with stable data structures.

### API

External API:

- Regions: `https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/regions`
- Planned Outages: `https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages`
- Probable Outages: `https://app.yasno.ua/api/blackout-service/public/shutdowns/probable-outages?regionId={region_id}&dsoId={dso_id}`

All HTTP requests use `aiohttp` (async, non-blocking). No authentication required.

For now, only planned outages are implemented. Probable outages support is planned in the future.

## Workflow

<instruction>Fill in by LLM assistant in memory</instruction>

This project is developed from Devcontainer described in `.devcontainer.json` file.

- **Adding/changing data fetching**
  - Extend `api.py` first; return Python objects (dicts/dataclasses) independent of raw JSON.
  - Use/extend `coordinator.py` to compute derived values (current state, next outage times).
  - Keep it simple: coordinator stored directly in `entry.runtime_data`.
- **Entities and platforms**
  - Add new sensor descriptors in `sensor.py` (use `translation_key`).
  - Unique ID format: `{entry_id}-{group}-{sensor_key}`; do not hardcode unique IDs in config flow.
  - Device naming uses `DeviceInfo` with translation placeholders: `{region}`, `{provider}`, `{group}`.
  - Calendar: Single calendar entity per entry showing all outage events with translated event names.
- **Config flow**
  - Multi-step: Region → Service (DSO) → Group
  - Auto-skip: If only one service available, auto-select it and skip to group step
  - Options flow: Same steps as config flow, allows reconfiguration
  - No duplicate detection needed: Each entry is unique (users may want multiple groups)
  - API calls in flow: Fetch regions list, then services for region, then groups for service
- **Repairs**
  - Purpose: Notify users about deprecated configuration (API v1 → v2 migration)
  - Detection: Check for `CONF_CITY` key (old format) in `entry.data` or `entry.options`
  - Action: Create non-fixable warning issue asking user to remove and re-add integration
- **Translations**
  - Edit `translations/*.json` directly (en.json, uk.json).
  - Translate values only; keep keys the same. Preserve placeholders: `{region}`, `{provider}`, `{group}`.
  - Structure: `config.step.*` (flows), `entity.{platform}.{key}` (entities), `device.*` (device naming), `common.*` (shared strings), `issues.*` (repairs).
- **When unsure**
  - Prefer adding debug logs and ask for the output to reason about runtime state.

### Develompent Scripts

- `scripts/setup` - installs dependencies and installs pre-commit.
- `scripts/develop` - starts a development Home Assistant instance on port 8123.
- `scripts/lint` - runs linter/formatter.
- `scripts/bump_version` - bumps version in manifest.json.

### Development Process

- Ask for clarification when requirements are ambiguous; surface 2–3 options when trade-offs matter.
- Update documentation and related rules when introducing new patterns or services.
- When unsure or need to make a significant decision ASK the user for guidance
- Do not commit anything. Leave commits to be done by a developer.

## Code Style

Use code style described in `.ruff.toml` configuration. Standard Python. 2-spaces indentation.

Never import modules in functions. All imports must be located on top of the file.

## Translations

- Translations: copy `translations/en.json` to add locales; translate values only where appropriate per HA guidelines.
- Entities: Use the `translation_key` defined in sensor/calendar entity descriptions.
- Placeholders: Reference `{region}`, `{provider}`, and `{group}` from `translation_placeholders` supplied by `device_info` when rendering device names.
- Add locales by copying `translations/en.json` and translating values per HA guidelines.

## Home Assistant API

Carefully read links to the Home Assistant Developer documentation for guidance.

Fetch these links to get more information about specific Home Assistant APIs directly from its documentation:

- File structure: https://developers.home-assistant.io/docs/creating_integration_file_structure
- Config Flow: https://developers.home-assistant.io/docs/config_entries_config_flow_handler
- Fetching data: https://developers.home-assistant.io/docs/integration_fetching_data
- Repairs: https://developers.home-assistant.io/docs/core/platform/repairs
- Sensor: https://developers.home-assistant.io/docs/core/entity/sensor
- Calendar: https://developers.home-assistant.io/docs/core/entity/calendar
- Config Entries: https://developers.home-assistant.io/docs/config_entries_index
- Data Entry Flow: https://developers.home-assistant.io/docs/data_entry_flow_index
- Manifest: https://developers.home-assistant.io/docs/creating_integration_manifest

## Important directives

<important>
If anything here is unclear (e.g., adding a new platform beyond sensors and calendar, or debugging with `debugpy`), tell me what you want to do and I'll expand these instructions.
</important>

<important>
If you struggle to find a solution, suggest to add logger statements and ask for output to get more context and understand the flow better. When logger output is provided, analyze it to understand what is going on.
</important>

<important>
When updating this file (`agents.md`), DON'T CHANGE the structure, formatting or style of the document. Just add relevant information, without restructuring: add list items, new sections, etc. NEVER REMOVE tags, like <important> or <instruction>.
</important>
