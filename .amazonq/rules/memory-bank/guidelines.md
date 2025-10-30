# Development Guidelines

## Code Quality Standards

### Formatting and Style
- **Linter**: Ruff (configured in .ruff.toml) for both linting and formatting
- **Line Length**: Standard Python conventions
- **Import Organization**: Standard library, third-party, local imports (separated by blank lines)
- **Type Hints**: Comprehensive type annotations on all function signatures (parameters and return types)
- **Docstrings**: Module-level and class-level docstrings using triple quotes
- **String Quotes**: Double quotes for strings throughout the codebase

### Naming Conventions
- **Classes**: PascalCase (e.g., `YasnoApi`, `IntegrationCoordinator`, `IntegrationSensor`)
- **Functions/Methods**: snake_case (e.g., `fetch_regions`, `get_current_event`, `async_step_user`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `LOGGER`, `SENSOR_TYPES`, `TIMEFRAME_TO_CHECK`)
- **Private Methods**: Prefix with single underscore (e.g., `_get_route_data`, `_parse_day_schedule`, `_event_to_state`)
- **Async Functions**: Prefix with `async_` for Home Assistant conventions (e.g., `async_setup_entry`, `async_fetch_translations`)

### Code Organization
- **Module Docstrings**: Every module starts with a docstring describing its purpose
- **Logging**: Module-level logger initialized as `LOGGER = logging.getLogger(__name__)`
- **Constants**: Imported from centralized `const.py` module
- **Type Annotations**: Use `|` for union types (e.g., `dict | None`, `int | None`)
- **Optional Parameters**: Use `None` as default with union type annotation

## Architectural Patterns

### Home Assistant Integration Patterns
```python
# Config flow pattern - multi-step user configuration
class YasnoOutagesConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_provider()
        # Show form logic
```

### DataUpdateCoordinator Pattern
```python
# Coordinator manages data fetching and state
class IntegrationCoordinator(DataUpdateCoordinator):
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=datetime.timedelta(minutes=UPDATE_INTERVAL),
        )
```

### Entity Implementation Pattern
```python
# Sensor entity with description-based configuration
@dataclass(frozen=True, kw_only=True)
class IntegrationSensorDescription(SensorEntityDescription):
    val_func: Callable[[IntegrationCoordinator], Any]

class IntegrationSensor(IntegrationEntity, SensorEntity):
    entity_description: IntegrationSensorDescription

    @property
    def native_value(self) -> str | None:
        return self.entity_description.val_func(self.coordinator)
```

## Async/Await Patterns

### Async HTTP Requests
```python
# Always use aiohttp with context managers and timeouts
async def _get_route_data(
    self,
    session: aiohttp.ClientSession,
    url: str,
    timeout_secs: int = 60,
) -> dict | None:
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout_secs),
        ) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError:
        LOGGER.exception("Error fetching data from %s", url)
        return None
```

### Async Method Naming
- Prefix all async methods with `async_` when following Home Assistant conventions
- Use `await` for all async calls
- Create new ClientSession for each request batch

## Error Handling

### Exception Handling Pattern
```python
# Catch specific exceptions, log with context, return None or safe default
try:
    updated_on = dt_utils.parse_datetime(group_data["updatedOn"])
    if updated_on:
        return dt_utils.as_local(updated_on)
except (ValueError, TypeError):
    LOGGER.warning(
        "Failed to parse updatedOn timestamp: %s",
        group_data["updatedOn"],
    )
    return None
```

### Validation Pattern
```python
# Validate configuration early with descriptive error messages
if not self.region:
    region_required_msg = (
        "Region not set in configuration - this should not happen "
        "with proper config flow"
    )
    region_error = "Region configuration is required"
    LOGGER.error(region_required_msg)
    raise ValueError(region_error)
```

## Testing Patterns

### Test Organization
```python
# Group tests by functionality using classes
class TestYasnoApiInit:
    """Test YasnoApi initialization."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        api = YasnoApi(region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP)
        assert api.region_id == TEST_REGION_ID
```

### Fixtures Pattern
```python
# Use pytest fixtures for reusable test data
@pytest.fixture(name="api")
def _api():
    """Create an API instance."""
    return YasnoApi(
        region_id=TEST_REGION_ID, provider_id=TEST_PROVIDER_ID, group=TEST_GROUP
    )

@pytest.fixture
def regions_data():
    """Sample regions data."""
    return [{"id": TEST_REGION_ID, "value": "Київ", "dsos": [...]}]
```

### Mocking Async HTTP

```python
# Mock aiohttp responses with AsyncMock
async def test_fetch_regions_success(self, api, regions_data):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=regions_data)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value.__aenter__.return_value = mock_response

        await api.fetch_yasno_regions()
        assert api.regions_data == regions_data
```

## Home Assistant Specific Patterns

### Translation Integration
```python
# Fetch and cache translations
async def async_fetch_translations(self) -> None:
    self.translations = await async_get_translations(
        self.hass,
        self.hass.config.language,
        "common",
        [DOMAIN],
    )
```

### Config Entry Data Access
```python
# Prefer options over data, with fallback
self.region = config_entry.options.get(
    CONF_REGION,
    config_entry.data.get(CONF_REGION),
)
```

### Entity Unique ID Pattern
```python
# Combine entry_id, group, and entity key for uniqueness
self._attr_unique_id = (
    f"{coordinator.config_entry.entry_id}-"
    f"{coordinator.group}-"
    f"{self.entity_description.key}"
)
```

### Selector Usage in Config Flow
```python
# Use SelectSelector for dropdown choices
vol.Required(CONF_REGION, default=default_value): SelectSelector(
    SelectSelectorConfig(
        options=region_options,
        translation_key="region",
    ),
)
```

## Data Model Patterns

### Dataclass Usage
```python
# Use frozen dataclasses for immutable entity descriptions
@dataclass(frozen=True, kw_only=True)
class IntegrationSensorDescription(SensorEntityDescription):
    val_func: Callable[[IntegrationCoordinator], Any]
```

### Enum for Event Types
```python
# Use enums for type-safe state management
class YasnoPlannedOutageEventType(Enum):
    DEFINITE = "Definite"
    EMERGENCY = "Emergency"
```

## Logging Best Practices

### Debug Logging
```python
# Use debug level for detailed operational information
LOGGER.debug("Group data for %s: %s", self.group, group_data)
LOGGER.debug("Next events: %s", next_events)
```

### Warning Logging
```python
# Use warning for unexpected but recoverable situations
LOGGER.warning("Unknown event type: %s", event.uid)
```

### Exception Logging
```python
# Use exception() to include traceback automatically
except aiohttp.ClientError:
    LOGGER.exception("Error fetching data from %s", url)
```

## Property Patterns

### Cached Properties
```python
# Cache computed values in private attributes
self._provider_name = ""  # Cache the provider name

@property
def provider_name(self) -> str:
    if self._provider_name:
        return self._simplify_provider_name(self._provider_name)
    # Fallback lookup logic
```

### Coordinator Properties
```python
# Expose coordinator data through properties
@property
def current_state(self) -> str:
    event = self.get_current_event()
    return self._event_to_state(event)
```

## DateTime Handling

### Use Home Assistant Utilities
```python
# Always use dt_utils for datetime operations
from homeassistant.util import dt as dt_utils

# Parse datetime strings
day_dt = dt_utils.parse_datetime(date_str)

# Get current time with timezone
now = dt_utils.now()

# Convert to local timezone
return dt_utils.as_local(updated_on)
```

### Time Conversion Pattern
```python
# Convert minutes from midnight to datetime
def _minutes_to_time(self, minutes: int, dt: datetime.datetime) -> datetime.datetime:
    hours = minutes // 60
    mins = minutes % 60

    # Handle end of day (24:00) - keep it as 23:59:59
    if hours == 24:
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    return dt.replace(hour=hours, minute=mins, second=0, microsecond=0)
```

## Code Comments

### Inline Documentation
- Use inline comments sparingly, prefer self-documenting code
- Add comments for complex business logic or non-obvious behavior
- Include example JSON structures in docstrings for API responses

### Debug Comments
```python
# DEBUG. DO NOT COMMIT UNCOMMENTED!
"""
self.planned_outage_data = {...}
"""
# DEBUG. DO NOT COMMIT UNCOMMENTED!
```

## Common Idioms

### List Comprehension with Filtering
```python
# Filter and transform in single expression
return [
    e for e in events
    if e.all_day or not (e.end <= start_date or e.start >= end_date)
]
```

### Dictionary Get with Fallback
```python
# Use .get() with default for safe dictionary access
status = day_data.get(BLOCK_KEY_STATUS)
providers = region_data.get("dsos", [])
```

### Walrus Operator for Assignment in Condition
```python
# Assign and check in single expression
if (provider_name := provider.get("name", "")) == self.provider:
    return self._simplify_provider_name(provider_name)
```

### Early Return Pattern
```python
# Return early for invalid states
if not self.planned_outage_data:
    return []
```
