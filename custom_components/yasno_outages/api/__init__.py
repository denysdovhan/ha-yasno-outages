"""The Yasno Outages API module."""

from .base import YasnoOutagesApi
from .weekly import YasnoWeeklyOutagesApi

__all__ = ["YasnoOutagesApi", "YasnoWeeklyOutagesApi"]
