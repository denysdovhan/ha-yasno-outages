# AI Coding Agents Guide

## Purpose

Agents act as senior Python collaborators. Keep responses concise,
clarify uncertainty before coding, and align suggestions with the rules linked below.

## Important directives

<important>
In all interactions and commit messages, be extremely concise and sacrifice grammar for the sake of concision.
</important>

<important>
If anything here is unclear, tell me what you want to do and I'll expand these instructions.
</important>

<important>
If you struggle to find a solution, suggest to add logger statements and ask for output to get more context and understand the flow better. When logger output is provided, analyze it to understand what is going on.
</important>

<important>
When updating this file (`agents.md`), DON'T CHANGE the structure, formatting or style of the document. Just add relevant information, without restructuring: add list items, new sections, etc. NEVER REMOVE tags, like <important> or <instruction>.
</important>

<important>
At the end of each plan, give me a list of unresolved questions to answer, if any. Make the questions extremely concise. Sacrifice grammar for the sake of concision.
</important>

## Project Overview

This repository is a Home Assistant custom integration providing electricity outage schedules for Ukraine using the [Yasno API](https://yasno.ua). Main codebase lives under `custom_components/yasno_outages`.

### Code structure

- `translations/` - folder containing translations (en.json, uk.json).
- `__init__.py` - init file of the integration, creates entries, sets up platforms, handles entry reload/unload. Stores runtime data (API, coordinator, integration) in `entry.runtime_data` as a `YasnoOutagesData` dataclass.
- `api.py` - a file containing an API class for fetching data. Should be Home Assistant agnostic, since in the future it's planned to move it to the separate package. Uses `aiohttp` for async HTTP requests.
- `config_flow.py` - a file describing a flow to create new entries and options flow for reconfiguration. Multi-step flow: region → service (DSO) → group.
- `const.py` - a file containing constants used throughout the project. Use `homeassistant.const` for commonly used constants.
- `coordinator.py` - a data fetching coordinator (`DataUpdateCoordinator`). Fetches data from the API, transforms it to the proper format, and passes them to sensors and calendar entities. Polls API every 15 minutes. Takes API instance as a parameter.
- `data.py` - defines runtime data types: `YasnoOutagesData` dataclass holding API, coordinator, and integration instances, and `YasnoOutagesConfigEntry` type alias for typed config entries.
- `entity.py` - a base entity class (`YasnoOutagesEntity`) that is used as a template when creating sensors and calendar. Contains important `DeviceInfo` joining different entities into a single device.
- `repairs.py` - repair flow for detecting and notifying users about deprecated configuration (API v1 → v2 migration).
- `manifest.json` - a file declaring an integration manifest.
- `sensor.py` - declares sensors using entity descriptors. Implements five sensors: electricity state (enum), schedule updated timestamp, next outage, next possible outage, next connectivity. Retrieves coordinator from `entry.runtime_data.coordinator`.
- `calendar.py` - implements calendar entity showing outage events in a timeline format. Retrieves coordinator from `entry.runtime_data.coordinator`.

<instruction>Fill in by LLM assistant memory</instruction>

### Using Coordinator to Fetch Data

We use a single `DataUpdateCoordinator` per config entry that polls the Yasno API every 15 minutes. The coordinator is created in `__init__.py` during setup and stored in `entry.runtime_data` as part of the `YasnoOutagesData` dataclass. Platforms (sensors, calendar) retrieve the coordinator from `config_entry.runtime_data.coordinator`.

The coordinator:

- Receives the API instance as a parameter (dependency injection)
- Resolves region/service names to IDs on first refresh
- Fetches outage schedules for the configured region, service (DSO), and group
- Transforms API data into `CalendarEvent` objects
- Computes derived values (current state, next outage times, etc.)

The runtime data pattern follows Home Assistant best practices:

- `data.py` defines `YasnoOutagesData` dataclass with API, coordinator, and integration
- `YasnoOutagesConfigEntry` type alias provides type safety for config entries
- API instance is created in `__init__.py` and passed to coordinator (decoupled initialization)
- Platforms access coordinator via `entry.runtime_data.coordinator`

Documentation: https://developers.home-assistant.io/docs/integration_fetching_data

### Decouple API Data from Coordinator

Coordinator should not rely on API response structure. Instead, transform data into plain Python objects (e.g., dataclasses) on API class level, so coordinator only calls API methods and works with stable data structures.

## API

External API:

- Regions: `https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/regions`
- Planned Outages:
  - Path: `https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages`
  - Example: `https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/25/dsos/902/planned-outages`
- Probable Outages (not implemented yet):
  - Path: `https://app.yasno.ua/api/blackout-service/public/shutdowns/probable-outages?regionId={region_id}&dsoId={dso_id}`
  - Example: `https://app.yasno.ua/api/blackout-service/public/shutdowns/probable-outages?regionId=25&dsoId=902`

All HTTP requests use `aiohttp` (async, non-blocking). No authentication required.

For now, only planned outages are implemented. Probable outages support is planned in the future.

### Planned Outages

Planned outages response have this scructure:

```json
{
  "1.1": {
    "today": {
      "slots": [
        {
          "start": 0,
          "end": 840,
          "type": "NotPlanned"
        },
        {
          "start": 840,
          "end": 1080,
          "type": "Definite"
        },
        {
          "start": 1080,
          "end": 1440,
          "type": "NotPlanned"
        }
      ],
      "date": "2025-11-05T00:00:00+02:00",
      "status": "ScheduleApplies"
    },
    "tomorrow": {
      "slots": [
        {
          "start": 0,
          "end": 1020,
          "type": "NotPlanned"
        },
        {
          "start": 1020,
          "end": 1200,
          "type": "Definite"
        },
        {
          "start": 1200,
          "end": 1440,
          "type": "NotPlanned"
        }
      ],
      "date": "2025-11-06T00:00:00+02:00",
      "status": "WaitingForSchedule"
    },
    "updatedOn": "2025-11-05T11:57:32+00:00"
  },
  "1.2": {}, // same structure
  "2.1": {}, // same structure
  "3.1": {}, // same structure
  "3.2": {}, // same structure
  "2.2": {}, // same structure
  "4.1": {}, // same structure
  "4.2": {}, // same structure
  "5.1": {}, // same structure
  "5.2": {}, // same structure
  "6.1": {}, // same structure
  "6.2": {} // same structure
}
```

#### Groups

Each group is coded as two digins `x.y`, `x` means group, `y` means subgroup. In planned outages each group have two properties `today` and `tomorrow`, describing tyime slots for outages.

#### Slots

Slots describe events. `start` and `end` are minutes in a day (from 0 to 1440). Slots can have these types:

- `NotPlaned` - no outages planned. Do not create any events from this type of slot.
- `Definite` - outage event. Event should be created for this time. This event should use date from `date` property.

#### Updated on

`updatedOn` property reflects when the schedule was updated by service provider (not the last time intergation fetched the data). There should be a sensor in `sensor.py` reflecting this value.

#### Status

Status property describes the type of the events and how to deal with them. There should be a sensor in `sensor.py` with corresponding status for `today`.

Here are types of statuses:

- `ScheduleApplies` - slots are applied. Events should be added to the calendar.
- `WaitingForSchedule` - slots are up for a changes. Created events, but they may be changed.
- `EmergencyShutdowns` - slots should be displayed in the calendar, but they are not active. Emmergency is happening.

### Probable Outages (not implemented yet)

Probable outages reflect the permanent schedule, that is active at all time. This integration should create recurring events for slots described in specificified group.

Planned outages is a specific clarification of how schedule looks today and tomorrow. Planned outages are kind of subset of probable outages.

Probable outages create a separate calendar entity describing only probable outages, skipping the days described in `today` and `tomorrow` properties of planned outages. Therefore, probable outages calendar should not contain any events for days described in planned outages.

Here is an example of response:

```json
{
  "25": {
    "dsos": {
      "902": {
        "groups": {
          "1.1": {
            "slots": {
              "0": [
                {
                  "start": 0,
                  "end": 300,
                  "type": "Definite"
                },
                {
                  "start": 300,
                  "end": 510,
                  "type": "NotPlanned"
                },
                {
                  "start": 510,
                  "end": 930,
                  "type": "Definite"
                },
                {
                  "start": 930,
                  "end": 1140,
                  "type": "NotPlanned"
                },
                {
                  "start": 1140,
                  "end": 1440,
                  "type": "Definite"
                }
              ],
              "1": [], // similar structure
              "2": [], // similar structure
              "3": [], // similar structure
              "4": [], // similar structure
              "5": [], // similar structure
              "6": [] // similar structure
            }
          },
          "1.2": {}, // similar structures
          "2.1": {}, // similar structures
          "2.2": {}, // similar structures
          "3.1": {}, // similar structures
          "3.2": {}, // similar structures
          "4.1": {}, // similar structures
          "4.2": {}, // similar structures
          "5.1": {}, // similar structures
          "5.2": {}, // similar structures
          "6.1": {}, // similar structures
          "6.2": {} // similar structures
        }
      }
    }
  }
}
```

Response contains region and service provider. `groups` property describes all available groups. Each group describes slots for each day of the week (from 0 to 6, meaning from monday to sunday). Each day has time slots for events with the same structure as planned outages.

`Definite` status for probable outages should create and event for probable outages.

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
- `scripts/develop` - starts a development Home Assistant server instance on port 8123. Use this script for checking changes in the browser.
- `scripts/lint` - runs linter/formatter. Always use this script for checking for errors and formatting.
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

## Commit messages

When generating commit messages, always use this format:

```
<type>(<scope>): summary up to 40 characters

Longer multiline description only for bigger changes that require additional explanations.
```

Summary should be concise and descriptive. Summary should not contain implicit or generic words like (enhance, improve, etc), instead it should clearly specify what is changed.

Use longer descriptions ocasionally to describe complex changes, only when it's really necessary.
