"""Shared definitions for storage configuration sections."""

from typing import Any, Final, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_STORAGE: Final = "storage"
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE: Final = "initial_charge"
CONF_INITIAL_CHARGE_PERCENTAGE: Final = "initial_charge_percentage"

type StorageValueConfig = str | float
type StorageValueData = NDArray[np.floating[Any]]


class StorageConfig(TypedDict):
    """Storage configuration for element types."""

    capacity: StorageValueConfig
    initial_charge: NotRequired[StorageValueConfig]
    initial_charge_percentage: NotRequired[StorageValueConfig]


class StorageData(TypedDict):
    """Loaded storage values for element types."""

    capacity: StorageValueData
    initial_charge: NotRequired[StorageValueData]
    initial_charge_percentage: NotRequired[StorageValueData]


class StorageSocConfig(TypedDict):
    """Storage config with required SOC percentage."""

    capacity: StorageValueConfig
    initial_charge_percentage: StorageValueConfig


class StorageSocData(TypedDict):
    """Loaded storage values with required SOC percentage."""

    capacity: StorageValueData
    initial_charge_percentage: StorageValueData


class StorageChargeConfig(TypedDict):
    """Storage config with required initial charge."""

    capacity: StorageValueConfig
    initial_charge: StorageValueConfig


class StorageChargeData(TypedDict):
    """Loaded storage values with required initial charge."""

    capacity: StorageValueData
    initial_charge: StorageValueData


def storage_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard storage section definition."""
    return SectionDefinition(key=SECTION_STORAGE, fields=fields, collapsed=collapsed)


def build_storage_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build storage field entries for config flows."""
    return {}


__all__ = [
    "CONF_CAPACITY",
    "CONF_INITIAL_CHARGE",
    "CONF_INITIAL_CHARGE_PERCENTAGE",
    "SECTION_STORAGE",
    "StorageChargeConfig",
    "StorageChargeData",
    "StorageConfig",
    "StorageData",
    "StorageSocConfig",
    "StorageSocData",
    "build_storage_fields",
    "storage_section",
]
