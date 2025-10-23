"""The Yasno Outages API module."""

from .base import YasnoOutagesApi, extract_group_index
from .weekly import YasnoWeeklyOutagesApi

__all__ = ["YasnoOutagesApi", "YasnoWeeklyOutagesApi", "extract_group_index"]
