"""Pure config transformation logic for v1.3 migration."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any, cast

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    SchemaValue,
    as_constant_value,
    as_entity_value,
    is_schema_value,
    normalize_connection_target,
)
from custom_components.haeo.core.schema.elements import (
    battery,
    battery_section,
    connection,
    grid,
    inverter,
    load,
    node,
    solar,
)
from custom_components.haeo.core.schema.sections import (
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


def migrate_element_config(data: Mapping[str, Any]) -> dict[str, Any] | None:
    """Migrate legacy element config to sectioned format.

    Takes a plain config dict and returns a migrated dict, or None if
    the element type is unknown or should be skipped.
    """
    data = dict(data)
    element_type = data.get(CONF_ELEMENT_TYPE)
    if not element_type or element_type == "network":
        return None

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
        undercharge: dict[str, Any] = {}
        overcharge: dict[str, Any] = {}

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
        if isinstance(data.get(battery.SECTION_UNDERCHARGE), dict):
            undercharge.update(data[battery.SECTION_UNDERCHARGE])
        if isinstance(data.get(battery.SECTION_OVERCHARGE), dict):
            overcharge.update(data[battery.SECTION_OVERCHARGE])
        convert_section_values(undercharge, (battery.CONF_PARTITION_PERCENTAGE, battery.CONF_PARTITION_COST))
        convert_section_values(overcharge, (battery.CONF_PARTITION_PERCENTAGE, battery.CONF_PARTITION_COST))

        migrated |= {
            SECTION_COMMON: common,
            battery.SECTION_STORAGE: storage,
            battery.SECTION_LIMITS: limits,
            SECTION_POWER_LIMITS: power_limits,
            SECTION_PRICING: pricing,
            SECTION_EFFICIENCY: efficiency,
            battery.SECTION_PARTITIONING: partitioning,
            battery.SECTION_UNDERCHARGE: undercharge,
            battery.SECTION_OVERCHARGE: overcharge,
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

        if isinstance(data.get(SECTION_PRICING), dict):
            pricing.update(data[SECTION_PRICING])
        convert_section_values(pricing, (CONF_PRICE_TARGET_SOURCE,))

        if isinstance(data.get(SECTION_CURTAILMENT), dict):
            curtailment.update(data[SECTION_CURTAILMENT])
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
