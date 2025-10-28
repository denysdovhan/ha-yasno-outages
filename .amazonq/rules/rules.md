- `custom_components/ha_power_outage_ua/manifest.json` is based on https://developers.home-assistant.io/docs/creating_integration_manifest/
- run precommit using "pre-commit run --all-files"
- run pytest using "uv run pytest"
- raise open questions before proceeding with implementations
- the tests should work around the main code, not vise versa
- calendar async_get_events incoming datetime objects are timezone-aware,
  so coordinator.get_events_between datetime objects are also timezone-aware,
  so api.get_events datetime objects are also timezone-aware
- the main code should not gain significant logic changes due to that the tests require them.
  it is better to work around the non-production environment differences inside the tests' code
- for multiple stages of an implementation use a markdown list.
  after implementing one of the steps mark it in the list and return the list
