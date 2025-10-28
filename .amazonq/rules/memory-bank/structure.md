# Project Structure

## Directory Organization

```
ha-svitlo-yeah/
├── custom_components/svitlo_yeah/    # Main integration code
│   ├── translations/                 # Localization files
│   ├── __init__.py                   # Integration setup and entry point
│   ├── api.py                        # API client for energy provider data
│   ├── calendar.py                   # Calendar entity implementation
│   ├── config_flow.py                # UI configuration flow
│   ├── const.py                      # Constants and configuration
│   ├── coordinator.py                # Data update coordinator
│   ├── entity.py                     # Base entity classes
│   ├── manifest.json                 # Integration metadata
│   ├── models.py                     # Data models
│   └── sensor.py                     # Sensor entity implementations
├── tests/                            # Test suite
│   ├── conftest.py                   # Pytest configuration and fixtures
│   ├── test_api.py                   # API tests
│   └── test_models.py                # Model tests
├── examples/                         # Usage examples
│   ├── automation.yaml               # Example automations
│   └── dashboard.yaml                # Example dashboard configuration
├── icons/                            # Integration icons and branding
├── media/                            # Documentation screenshots
├── .github/workflows/                # CI/CD pipelines
├── script/                           # Development scripts
├── pyproject.toml                    # Python project configuration
├── hacs.json                         # HACS integration metadata
└── README.md                         # User documentation
```

## Core Components

### Integration Layer (`custom_components/svitlo_yeah/`)
- **__init__.py**: Entry point, handles integration setup, platform loading, and lifecycle management
- **config_flow.py**: Implements Home Assistant's config flow for UI-based setup (region, provider, group selection)
- **const.py**: Centralized constants including domain name, entity types, and configuration keys

### Data Layer
- **api.py**: API client that communicates with Ukrainian energy provider services to fetch outage schedules
- **models.py**: Data models representing outage schedules, regions, providers, and groups
- **coordinator.py**: DataUpdateCoordinator implementation that manages periodic data fetching and state updates

### Entity Layer
- **entity.py**: Base entity classes providing common functionality for all integration entities
- **sensor.py**: Sensor entities exposing outage status, countdown timers, and schedule information
- **calendar.py**: Calendar entity providing outage schedule in Home Assistant calendar format

### Localization
- **translations/**: Multi-language support for UI strings (Ukrainian, English)

## Architectural Patterns

### Home Assistant Integration Pattern
Follows standard Home Assistant integration architecture:
1. Config flow for user-friendly setup
2. DataUpdateCoordinator for efficient data fetching
3. Entity platform implementations (sensor, calendar)
4. Manifest-based metadata and dependencies

### Data Flow
1. User configures region/provider/group via config flow
2. Coordinator periodically fetches data from API
3. API client retrieves outage schedules from provider
4. Models parse and structure the data
5. Entities expose data as sensors and calendar events
6. Home Assistant updates UI and triggers automations

### Separation of Concerns
- API logic isolated in api.py
- Business logic in coordinator and models
- Presentation logic in entity implementations
- Configuration logic in config_flow.py
- Constants centralized in const.py

### Async/Await Pattern
All I/O operations use async/await for non-blocking execution, following Home Assistant best practices.
