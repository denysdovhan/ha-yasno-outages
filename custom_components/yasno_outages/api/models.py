"""Data models for Yasno outages API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class YasnoApiError(Exception):
    """Raised when Yasno API request fails."""


class YasnoNotFoundError(YasnoApiError):
    """Raised when Yasno API returns 404."""


class OutageEventType(StrEnum):
    """Outage event types."""

    DEFINITE = "Definite"
    NOT_PLANNED = "NotPlanned"


class OutageSource(StrEnum):
    """Source type for outage events."""

    PLANNED = "planned"
    PROBABLE = "probable"


@dataclass(frozen=True)
class OutageEvent:
    """Represents an outage event."""

    event_type: OutageEventType
    start: datetime
    end: datetime
    source: OutageSource


@dataclass(frozen=True)
class OutageSlot:
    """Represents an outage time slot template."""

    start: int  # Minutes from midnight
    end: int  # Minutes from midnight
    event_type: OutageEventType


@dataclass(frozen=True)
class AuthTokens:
    """OAuth2 tokens obtained from the authenticated (account) login flow."""

    access_token: str
    refresh_token: str
    id_token: str
    expires_in: int  # Seconds until access_token expiry, from the token response


@dataclass(frozen=True)
class YasnoAccount:
    """Represents a logged-in user's account (address, tariff, supplier)."""

    id: int
    account_number: str
    account_name: str
    customer_type: str
    address: str
    supplier: str
    region: str
    billing_status: str


@dataclass(frozen=True)
class YasnoContract:
    """Represents a contract entry (account + current balance/debt)."""

    id: int
    name: str
    application_type: str
    debt: float
    account_number: str
    address: str
    region: str
    supplier: str
    billing_status: str
    can_be_paid: bool


@dataclass(frozen=True)
class YasnoMeterReading:
    """Represents the last submitted meter reading for an account."""

    created_on: datetime.datetime | None
    owner: str
    reading_method: str
    day_value: float | None
    night_value: float | None


@dataclass(frozen=True)
class YasnoAccountDebt:
    """Represents the balance/debt and last meter reading for an account."""

    balance: float
    electric_meter_exists: bool
    has_invoice_file: bool
    is_paper_bill_required: bool
    last_meter_reading: YasnoMeterReading | None


@dataclass(frozen=True)
class YasnoAuthAddress:
    """Represents an address linked to the logged-in account, with its group."""

    address_id: int
    name: str
    region_id: int
    group: int
    subgroup: int
    dso_id: int
    dso_name: str


@dataclass(frozen=True)
class YasnoTariffPrice:
    """Represents a single zone (Day/Night/AllTime) price within a tariff tier."""

    zone: str
    price: float


@dataclass(frozen=True)
class YasnoTariffTier:
    """Represents a consumption-volume tier within a tariff period."""

    name: str | None
    prices: tuple[YasnoTariffPrice, ...]
    for_all_volume: bool

    def price_for_zone(self, zone: str) -> float | None:
        """Get the price for a specific zone (e.g. Day/Night) in this tier."""
        for price in self.prices:
            if price.zone == zone:
                return price.price
        return None


@dataclass(frozen=True)
class YasnoTariffPeriod:
    """Represents a tariff period (date range) with its pricing tiers."""

    start_date: datetime.datetime
    end_date: datetime.datetime
    tiers: tuple[YasnoTariffTier, ...]

    def is_active(self, at: datetime.datetime) -> bool:
        """
        Return True if this period applies at the given date/time.

        Compares month/day only (ignoring year), since Yasno's API returns
        recurring seasonal periods whose year components are inconsistent
        (e.g. a period can have a startDate in a later year than its
        endDate). This also correctly handles periods that wrap across a
        year boundary (e.g. October to April).
        """
        start_md = (self.start_date.month, self.start_date.day)
        end_md = (self.end_date.month, self.end_date.day)
        at_md = (at.month, at.day)
        if start_md <= end_md:
            return start_md <= at_md <= end_md
        return at_md >= start_md or at_md <= end_md

    def base_tier(self) -> YasnoTariffTier | None:
        """Get the base (lowest-volume) consumption tier, if any."""
        return self.tiers[0] if self.tiers else None


@dataclass(frozen=True)
class YasnoTariff:
    """Represents the tariff plan for a logged-in account."""

    name: str
    dso_name: str
    distribution_price: float | None
    transfer_price: float | None
    periods: tuple[YasnoTariffPeriod, ...]

    def active_period(self, at: datetime.datetime) -> YasnoTariffPeriod | None:
        """Get the tariff period active at the given date/time, if any."""
        for period in self.periods:
            if period.is_active(at):
                return period
        return None

    def price_for_zone(self, at: datetime.datetime, zone: str) -> float | None:
        """Get the base-tier price for a zone at the given date/time."""
        period = self.active_period(at)
        if not period:
            return None
        tier = period.base_tier()
        if not tier:
            return None
        return tier.price_for_zone(zone)
