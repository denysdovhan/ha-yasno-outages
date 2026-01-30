"""Tests for entity helpers."""

from unittest.mock import MagicMock

from custom_components.yasno_outages.entity import YasnoOutagesEntity


class DummyEntity(YasnoOutagesEntity):
    """Test entity for device info assertions."""


def _build_coordinator(address_name: str | None, group: str) -> MagicMock:
    coordinator = MagicMock()
    coordinator.region_name = "Kyiv"
    coordinator.address_name = address_name
    coordinator.group = group
    coordinator.config_entry = MagicMock(entry_id="entry-id")
    return coordinator


def test_device_info_uses_address_name():
    """Device info uses address when present."""
    entity = DummyEntity(_build_coordinator("Main St 12", "1.1"))
    placeholders = entity.device_info["translation_placeholders"]
    assert placeholders["address"] == "Main St 12"


def test_device_info_falls_back_to_group():
    """Device info falls back to group when address missing."""
    entity = DummyEntity(_build_coordinator(None, "1.1"))
    placeholders = entity.device_info["translation_placeholders"]
    assert placeholders["address"] == "1.1"
