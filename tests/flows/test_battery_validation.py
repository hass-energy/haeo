"""Test battery soft limit validation in configuration flows."""

from custom_components.haeo.elements.battery import (
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_OVERCHARGE_COST,
    CONF_SOFT_MAX_CHARGE_PERCENTAGE,
    CONF_SOFT_MIN_CHARGE_PERCENTAGE,
    CONF_UNDERCHARGE_COST,
)
from custom_components.haeo.flows.element import ElementSubentryFlow


def test_validate_overcharge_fields_incomplete_missing_cost() -> None:
    """Test validation fails when soft_max provided without overcharge_cost."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_SOFT_MAX_CHARGE_PERCENTAGE: 80.0,
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert "overcharge_fields_incomplete" in errors.values()


def test_validate_overcharge_fields_incomplete_missing_soft_max() -> None:
    """Test validation fails when overcharge_cost provided without soft_max."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_OVERCHARGE_COST: 5.0,
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert "overcharge_fields_incomplete" in errors.values()


def test_validate_undercharge_fields_incomplete_missing_cost() -> None:
    """Test validation fails when soft_min provided without undercharge_cost."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_SOFT_MIN_CHARGE_PERCENTAGE: 20.0,
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert "undercharge_fields_incomplete" in errors.values()


def test_validate_undercharge_fields_incomplete_missing_soft_min() -> None:
    """Test validation fails when undercharge_cost provided without soft_min."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_UNDERCHARGE_COST: 3.0,
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert "undercharge_fields_incomplete" in errors.values()


def test_validate_invalid_soft_charge_range_soft_min_below_min() -> None:
    """Test validation fails when soft_min < min."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
        CONF_SOFT_MIN_CHARGE_PERCENTAGE: 5.0,
        CONF_SOFT_MAX_CHARGE_PERCENTAGE: 80.0,
        CONF_UNDERCHARGE_COST: 2.0,
        CONF_OVERCHARGE_COST: 4.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert "invalid_soft_charge_range" in errors.values()


def test_validate_invalid_soft_charge_range_soft_max_above_max() -> None:
    """Test validation fails when soft_max > max."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
        CONF_SOFT_MIN_CHARGE_PERCENTAGE: 20.0,
        CONF_SOFT_MAX_CHARGE_PERCENTAGE: 95.0,
        CONF_UNDERCHARGE_COST: 2.0,
        CONF_OVERCHARGE_COST: 4.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert "invalid_soft_charge_range" in errors.values()


def test_validate_invalid_soft_charge_range_soft_min_equals_soft_max() -> None:
    """Test validation fails when soft_min >= soft_max."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
        CONF_SOFT_MIN_CHARGE_PERCENTAGE: 50.0,
        CONF_SOFT_MAX_CHARGE_PERCENTAGE: 50.0,
        CONF_UNDERCHARGE_COST: 2.0,
        CONF_OVERCHARGE_COST: 4.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert "invalid_soft_charge_range" in errors.values()


def test_validate_valid_soft_limits() -> None:
    """Test validation passes with valid soft limits."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
        CONF_SOFT_MIN_CHARGE_PERCENTAGE: 20.0,
        CONF_SOFT_MAX_CHARGE_PERCENTAGE: 80.0,
        CONF_UNDERCHARGE_COST: 2.0,
        CONF_OVERCHARGE_COST: 4.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert len(errors) == 0


def test_validate_no_soft_limits() -> None:
    """Test validation passes when no soft limits configured."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert len(errors) == 0


def test_validate_only_overcharge() -> None:
    """Test validation passes with only overcharge soft limit."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
        CONF_SOFT_MAX_CHARGE_PERCENTAGE: 80.0,
        CONF_OVERCHARGE_COST: 5.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert len(errors) == 0


def test_validate_only_undercharge() -> None:
    """Test validation passes with only undercharge soft limit."""
    flow = ElementSubentryFlow("battery", dict, {})

    user_input = {
        CONF_MIN_CHARGE_PERCENTAGE: 10.0,
        CONF_MAX_CHARGE_PERCENTAGE: 90.0,
        CONF_SOFT_MIN_CHARGE_PERCENTAGE: 20.0,
        CONF_UNDERCHARGE_COST: 3.0,
    }

    errors = flow._validate_battery_soft_limits(user_input)
    assert len(errors) == 0
