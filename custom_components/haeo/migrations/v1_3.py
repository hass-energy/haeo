"""Migration helpers for config entry version 1.3."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from numbers import Real
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
)
from custom_components.haeo.flows import (
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.schema import (
    SchemaValue,
    as_constant_value,
    as_entity_value,
    is_schema_value,
    normalize_connection_target,
)

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 3


def _migrate_hub_data(entry: ConfigEntry) -> tuple[dict[str, Any], dict[str, Any]]:
    """Migrate hub entry data/options into sectioned config data."""
    data = dict(entry.data)
    options = dict(entry.options)

    if "basic" in data and HUB_SECTION_COMMON not in data:
        data[HUB_SECTION_COMMON] = data.pop("basic")

    if HUB_SECTION_COMMON in data and HUB_SECTION_ADVANCED in data and HUB_SECTION_TIERS in data:
        return data, options

    horizon_preset = options.get(CONF_HORIZON_PRESET) or data.get(CONF_HORIZON_PRESET) or HORIZON_PRESET_5_DAYS
    tiers = {
        CONF_TIER_1_COUNT: options.get(CONF_TIER_1_COUNT, DEFAULT_TIER_1_COUNT),
        CONF_TIER_1_DURATION: options.get(CONF_TIER_1_DURATION, DEFAULT_TIER_1_DURATION),
        CONF_TIER_2_COUNT: options.get(CONF_TIER_2_COUNT, DEFAULT_TIER_2_COUNT),
        CONF_TIER_2_DURATION: options.get(CONF_TIER_2_DURATION, DEFAULT_TIER_2_DURATION),
        CONF_TIER_3_COUNT: options.get(CONF_TIER_3_COUNT, DEFAULT_TIER_3_COUNT),
        CONF_TIER_3_DURATION: options.get(CONF_TIER_3_DURATION, DEFAULT_TIER_3_DURATION),
        CONF_TIER_4_COUNT: options.get(CONF_TIER_4_COUNT, DEFAULT_TIER_4_COUNT),
        CONF_TIER_4_DURATION: options.get(CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION),
    }
    advanced = {
        CONF_DEBOUNCE_SECONDS: options.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS),
        CONF_ADVANCED_MODE: options.get(CONF_ADVANCED_MODE, False),
    }

    data[HUB_SECTION_COMMON] = {CONF_NAME: data.get(CONF_NAME, entry.title), CONF_HORIZON_PRESET: horizon_preset}
    data[HUB_SECTION_TIERS] = tiers
    data[HUB_SECTION_ADVANCED] = advanced

    for key in (
        CONF_NAME,
        CONF_HORIZON_PRESET,
        CONF_ADVANCED_MODE,
        CONF_DEBOUNCE_SECONDS,
        CONF_TIER_1_COUNT,
        CONF_TIER_1_DURATION,
        CONF_TIER_2_COUNT,
        CONF_TIER_2_DURATION,
        CONF_TIER_3_COUNT,
        CONF_TIER_3_DURATION,
        CONF_TIER_4_COUNT,
        CONF_TIER_4_DURATION,
    ):
        data.pop(key, None)

    return data, {}


def _migrate_subentry_data(subentry: ConfigSubentry) -> dict[str, Any] | None:
    """Migrate a subentry's data to sectioned config if needed."""
    data = dict(subentry.data)
    element_type = data.get(CONF_ELEMENT_TYPE)
    if not element_type or element_type == ELEMENT_TYPE_NETWORK:
        return None

    from custom_components.haeo.elements import (  # noqa: PLC0415
        battery,
        battery_section,
        connection,
        grid,
        inverter,
        load,
        node,
        solar,
    )
    from custom_components.haeo.sections import (  # noqa: PLC0415
        CONF_CONNECTION,
        CONF_CURTAILMENT,
        CONF_FORECAST,
        CONF_MAX_POWER_SOURCE_TARGET,
        CONF_MAX_POWER_TARGET_SOURCE,
        CONF_PRICE_SOURCE_TARGET,
        CONF_PRICE_TARGET_SOURCE,
        SECTION_COMMON,
        SECTION_CURTAILMENT,
        SECTION_EFFICIENCY,
        SECTION_FORECAST,
        SECTION_POWER_LIMITS,
        SECTION_PRICING,
    )

    def get_value(key: str) -> Any | None:
        if key in data:
            return data[key]
        for value in data.values():
            if isinstance(value, Mapping):
                mapping_value = cast("Mapping[str, Any]", value)
                if key in mapping_value:
                    return mapping_value[key]
        return None

    def to_schema_value(value: Any) -> SchemaValue:
        if is_schema_value(value):
            return value
        if isinstance(value, bool):
            return as_constant_value(value)
        if isinstance(value, Real):
            return as_constant_value(float(value))
        if isinstance(value, str):
            return as_entity_value([value])
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return as_entity_value(value)
        msg = f"Unsupported schema value {value!r}"
        raise TypeError(msg)

    def add_if_present(target: dict[str, Any], key: str, *, convert: bool = False) -> None:
        value = get_value(key)
        if value is not None:
            target[key] = to_schema_value(value) if convert else value

    def convert_section_values(section: dict[str, Any], keys: tuple[str, ...]) -> None:
        for key in keys:
            if key in section:
                section[key] = to_schema_value(section[key])

    migrated: dict[str, Any] = {CONF_ELEMENT_TYPE: element_type}

    if element_type == battery.ELEMENT_TYPE:
        common: dict[str, Any] = {}
        storage: dict[str, Any] = {}
        limits: dict[str, Any] = {}
        power_limits: dict[str, Any] = {}
        pricing: dict[str, Any] = {}
        efficiency: dict[str, Any] = {}
        partitioning: dict[str, Any] = {}

        for key in (CONF_NAME, CONF_CONNECTION):
            add_if_present(common, key)
        if CONF_CONNECTION in common:
            common[CONF_CONNECTION] = normalize_connection_target(common[CONF_CONNECTION])
        for key in (battery.CONF_CAPACITY, battery.CONF_INITIAL_CHARGE_PERCENTAGE):
            add_if_present(storage, key, convert=True)
        for key in (
            battery.CONF_MIN_CHARGE_PERCENTAGE,
            battery.CONF_MAX_CHARGE_PERCENTAGE,
        ):
            add_if_present(limits, key, convert=True)
        for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE):
            add_if_present(power_limits, key, convert=True)
        if (legacy_max_charge := get_value("max_charge_power")) is not None:
            power_limits.setdefault(CONF_MAX_POWER_TARGET_SOURCE, to_schema_value(legacy_max_charge))
        if (legacy_max_discharge := get_value("max_discharge_power")) is not None:
            power_limits.setdefault(CONF_MAX_POWER_SOURCE_TARGET, to_schema_value(legacy_max_discharge))
        for key in (CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE):
            add_if_present(pricing, key, convert=True)
        if (legacy_discharge_cost := get_value("discharge_cost")) is not None:
            pricing.setdefault(CONF_PRICE_SOURCE_TARGET, to_schema_value(legacy_discharge_cost))
        if (legacy_charge_incentive := get_value("early_charge_incentive")) is not None:
            pricing.setdefault(CONF_PRICE_TARGET_SOURCE, to_schema_value(legacy_charge_incentive))
        for key in (battery.CONF_EFFICIENCY_SOURCE_TARGET, battery.CONF_EFFICIENCY_TARGET_SOURCE):
            add_if_present(efficiency, key, convert=True)
        if (legacy_efficiency := get_value("efficiency")) is not None:
            efficiency.setdefault(battery.CONF_EFFICIENCY_SOURCE_TARGET, to_schema_value(legacy_efficiency))
            efficiency.setdefault(battery.CONF_EFFICIENCY_TARGET_SOURCE, to_schema_value(legacy_efficiency))
        add_if_present(partitioning, battery.CONF_CONFIGURE_PARTITIONS)

        migrated |= {
            SECTION_COMMON: common,
            battery.SECTION_STORAGE: storage,
            battery.SECTION_LIMITS: limits,
            SECTION_POWER_LIMITS: power_limits,
            SECTION_PRICING: pricing,
            SECTION_EFFICIENCY: efficiency,
            battery.SECTION_PARTITIONING: partitioning,
        }
        return migrated

    if element_type == battery_section.ELEMENT_TYPE:
        common: dict[str, Any] = {}
        storage: dict[str, Any] = {}
        add_if_present(common, CONF_NAME)
        add_if_present(storage, battery_section.CONF_CAPACITY, convert=True)
        add_if_present(storage, battery_section.CONF_INITIAL_CHARGE, convert=True)
        migrated |= {
            SECTION_COMMON: common,
            battery_section.SECTION_STORAGE: storage,
        }
        return migrated

    if element_type == connection.ELEMENT_TYPE:
        common: dict[str, Any] = {}
        endpoints: dict[str, Any] = {}
        power_limits: dict[str, Any] = {}
        pricing: dict[str, Any] = {}
        efficiency: dict[str, Any] = {}
        add_if_present(common, CONF_NAME)
        for key in (connection.CONF_SOURCE, connection.CONF_TARGET):
            add_if_present(endpoints, key)
        for key in (connection.CONF_SOURCE, connection.CONF_TARGET):
            if key in endpoints:
                endpoints[key] = normalize_connection_target(endpoints[key])
        for key in (connection.CONF_MAX_POWER_SOURCE_TARGET, connection.CONF_MAX_POWER_TARGET_SOURCE):
            add_if_present(power_limits, key, convert=True)
        for key in (connection.CONF_PRICE_SOURCE_TARGET, connection.CONF_PRICE_TARGET_SOURCE):
            add_if_present(pricing, key, convert=True)
        for key in (connection.CONF_EFFICIENCY_SOURCE_TARGET, connection.CONF_EFFICIENCY_TARGET_SOURCE):
            add_if_present(efficiency, key, convert=True)
        migrated |= {
            SECTION_COMMON: common,
            connection.SECTION_ENDPOINTS: endpoints,
            SECTION_POWER_LIMITS: power_limits,
            SECTION_PRICING: pricing,
            SECTION_EFFICIENCY: efficiency,
        }
        return migrated

    if element_type == grid.ELEMENT_TYPE:
        common: dict[str, Any] = {}
        pricing: dict[str, Any] = {}
        power_limits: dict[str, Any] = {}
        for key in (CONF_NAME, CONF_CONNECTION):
            add_if_present(common, key)
        if CONF_CONNECTION in common:
            common[CONF_CONNECTION] = normalize_connection_target(common[CONF_CONNECTION])
        for key in (CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE):
            add_if_present(pricing, key, convert=True)
        if (legacy_import_price := get_value("import_price")) is not None:
            pricing.setdefault(CONF_PRICE_SOURCE_TARGET, to_schema_value(legacy_import_price))
        if (legacy_export_price := get_value("export_price")) is not None:
            pricing.setdefault(CONF_PRICE_TARGET_SOURCE, to_schema_value(legacy_export_price))
        for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE):
            add_if_present(power_limits, key, convert=True)
        if (legacy_import_limit := get_value("import_limit")) is not None:
            power_limits.setdefault(CONF_MAX_POWER_SOURCE_TARGET, to_schema_value(legacy_import_limit))
        if (legacy_export_limit := get_value("export_limit")) is not None:
            power_limits.setdefault(CONF_MAX_POWER_TARGET_SOURCE, to_schema_value(legacy_export_limit))
        migrated |= {
            SECTION_COMMON: common,
            SECTION_PRICING: pricing,
            SECTION_POWER_LIMITS: power_limits,
        }
        return migrated

    if element_type == inverter.ELEMENT_TYPE:
        common: dict[str, Any] = {}
        power_limits: dict[str, Any] = {}
        efficiency: dict[str, Any] = {}
        for key in (CONF_NAME, CONF_CONNECTION):
            add_if_present(common, key)
        if CONF_CONNECTION in common:
            common[CONF_CONNECTION] = normalize_connection_target(common[CONF_CONNECTION])
        for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE):
            add_if_present(power_limits, key, convert=True)
        if (legacy_dc_to_ac := get_value("max_power_dc_to_ac")) is not None:
            power_limits.setdefault(CONF_MAX_POWER_SOURCE_TARGET, to_schema_value(legacy_dc_to_ac))
        if (legacy_ac_to_dc := get_value("max_power_ac_to_dc")) is not None:
            power_limits.setdefault(CONF_MAX_POWER_TARGET_SOURCE, to_schema_value(legacy_ac_to_dc))
        for key in (inverter.CONF_EFFICIENCY_SOURCE_TARGET, inverter.CONF_EFFICIENCY_TARGET_SOURCE):
            add_if_present(efficiency, key, convert=True)
        if (legacy_dc_to_ac := get_value("efficiency_dc_to_ac")) is not None:
            efficiency.setdefault(inverter.CONF_EFFICIENCY_SOURCE_TARGET, to_schema_value(legacy_dc_to_ac))
        if (legacy_ac_to_dc := get_value("efficiency_ac_to_dc")) is not None:
            efficiency.setdefault(inverter.CONF_EFFICIENCY_TARGET_SOURCE, to_schema_value(legacy_ac_to_dc))
        migrated |= {
            SECTION_COMMON: common,
            SECTION_POWER_LIMITS: power_limits,
            SECTION_EFFICIENCY: efficiency,
        }
        return migrated

    if element_type == load.ELEMENT_TYPE:
        common: dict[str, Any] = {}
        forecast: dict[str, Any] = {}
        pricing: dict[str, Any] = {}
        curtailment: dict[str, Any] = {}
        for key in (CONF_NAME, CONF_CONNECTION):
            add_if_present(common, key)
        if CONF_CONNECTION in common:
            common[CONF_CONNECTION] = normalize_connection_target(common[CONF_CONNECTION])
        add_if_present(forecast, CONF_FORECAST, convert=True)

        # Backfill required sections introduced after 1.3's original load schema.
        #
        # Pricing is optional/disableable (NoneValue) but the section itself is required.
        if isinstance(data.get(SECTION_PRICING), dict):
            pricing.update(data[SECTION_PRICING])
        convert_section_values(pricing, (CONF_PRICE_TARGET_SOURCE,))

        if isinstance(data.get(SECTION_CURTAILMENT), dict):
            curtailment.update(data[SECTION_CURTAILMENT])
        # Legacy section/field name (from early development) was "shedding".
        if isinstance(data.get("shedding"), dict) and CONF_CURTAILMENT not in curtailment:
            legacy = data["shedding"]
            if "shedding" in legacy:
                curtailment[CONF_CURTAILMENT] = to_schema_value(legacy["shedding"])
        convert_section_values(curtailment, (CONF_CURTAILMENT,))

        migrated |= {
            SECTION_COMMON: common,
            SECTION_FORECAST: forecast,
            SECTION_PRICING: pricing,
            SECTION_CURTAILMENT: curtailment,
        }
        return migrated

    if element_type == node.ELEMENT_TYPE:
        common: dict[str, Any] = {}
        role: dict[str, Any] = {}
        add_if_present(common, CONF_NAME)
        for key in (node.CONF_IS_SOURCE, node.CONF_IS_SINK):
            add_if_present(role, key)
        migrated |= {
            SECTION_COMMON: common,
            node.SECTION_ROLE: role,
        }
        return migrated

    if element_type == solar.ELEMENT_TYPE:
        common: dict[str, Any] = {}
        forecast: dict[str, Any] = {}
        pricing: dict[str, Any] = {}
        curtailment: dict[str, Any] = {}
        for key in (CONF_NAME, CONF_CONNECTION):
            add_if_present(common, key)
        if CONF_CONNECTION in common:
            common[CONF_CONNECTION] = normalize_connection_target(common[CONF_CONNECTION])
        add_if_present(forecast, CONF_FORECAST, convert=True)
        add_if_present(pricing, CONF_PRICE_SOURCE_TARGET, convert=True)
        if (legacy_production_price := get_value("price_production")) is not None:
            pricing.setdefault(CONF_PRICE_SOURCE_TARGET, to_schema_value(legacy_production_price))
        add_if_present(curtailment, solar.CONF_CURTAILMENT, convert=True)
        migrated |= {
            SECTION_COMMON: common,
            SECTION_FORECAST: forecast,
            SECTION_PRICING: pricing,
            solar.SECTION_CURTAILMENT: curtailment,
        }
        return migrated

    return None


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.3."""
    if entry.minor_version >= MINOR_VERSION:
        return True

    _LOGGER.info(
        "Migrating %s entry %s to version 1.%s",
        DOMAIN,
        entry.entry_id,
        MINOR_VERSION,
    )

    new_data, new_options = _migrate_hub_data(entry)
    hass.config_entries.async_update_entry(
        entry,
        data=new_data,
        options=new_options,
        minor_version=MINOR_VERSION,
    )

    for subentry in entry.subentries.values():
        migrated = _migrate_subentry_data(subentry)
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)

    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True
