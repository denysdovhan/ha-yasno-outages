# Copilot Instructions for HA Yasno Outages

## Project Overview

This is a **Home Assistant custom integration** that tracks electricity outage schedules in Ukraine using the Yasno API. The integration provides calendar entities and sensors for monitoring planned power outages by region, provider (DSO), and group.

## Architecture

Main integration code resides in `custom_components/yasno_outages/` folder.

### Core Components

- `api.py`: Async HTTP client using `aiohttp` to fetch regions, providers, and outage schedules from Yasno's public API
- `coordinator.py`: `DataUpdateCoordinator` that polls API every 15 minutes, manages state, and transforms API data into Home Assistant entities
- `config_flow.py`: Multi-step UI configuration
- `calendar.py`: Calendar entity showing outage events
- `sensor.py`: Four sensors: electricity state (enum), schedule update timestamp, next outage time, next connectivity time
- `entity.py`: Base entity class providing device info with region/provider/group

## Critical Patterns

### Using Coordinator to Fetch Data

The `DataUpdateCoordinator` is used to fetch data from the Yasno API and make it available to Home Assistant entities. It handles polling the API at regular intervals and manages the state of the data.

Documentation: https://developers.home-assistant.io/docs/integration_fetching_data

### Decouple API Data from Coordinator

Coordinator should not rely on API response structure. Instead, transform data into plain Python objects (e.g., dataclasses) on API class level, so coordinator only calls API methods and works with stable data structures.

### API Time Handling

The API returns time slots as **minutes from midnight** (0-1440). Convert using `_minutes_to_time()`:

```python
# Handle end-of-day edge case (24:00 = 23:59:59)
if hours == 24:
    return date.replace(hour=23, minute=59, second=59, microsecond=999999)
```

### Entity Unique IDs

Format: `{entry_id}-{group}-{entity_key}` (e.g., `abc123-1.1-electricity`)

### Repair for configuration changes

Home Assistant keeps track of issues which should be brought to the user's attention. These issues can be created by integrations or by Home Assistant itself.

Documentation: https://developers.home-assistant.io/docs/core/platform/repairs

Example:

```py
from homeassistant.helpers import issue_registry as ir

ir.async_create_issue(
    hass,
    DOMAIN,
    "manual_migration",
    breaks_in_ha_version="2022.9.0",
    is_fixable=False,
    severity=ir.IssueSeverity.ERROR,
    translation_key="manual_migration",
)
```

## Development Workflow

### Local Testing

```bash
scripts/develop  # Starts HA on port 8123 with PYTHONPATH set to custom_components
```

Integration auto-loads from `custom_components/yasno_outages/`. Config stored in `config/` dir.

### Code Quality

- **Linter**: Ruff with aggressive rule set (see `.ruff.toml`)
- **Max complexity**: 25 (McCabe)
- **Python**: 3.13 target
- **Import order**: Use `from __future__ import annotations` for forward refs

### Translation Files

Add translations to `translations/{lang}.json`. Structure:

- `config.step.*`: Config flow UI
- `entity.{platform}.{key}`: Entity names and states
- `common.event_name_*`: Calendar event names
- `issues.*`: Repair issue messages

## Key Constraints

1. **No blocking I/O**: Use `aiohttp`, never `requests`
2. **ID resolution**: Always resolve region/provider names to IDs before creating API instance with IDs
3. **Config vs Options**: Check both `config_entry.options` and `config_entry.data` (options override data)
4. **Date ranges**: Filter events by intersection with requested range, not just start time

## API Endpoints

- Regions: `https://app.yasno.ua/api/blackout-service/public/shutdowns/addresses/v2/regions`
- Outages: `https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region_id}/dsos/{dso_id}/planned-outages`
