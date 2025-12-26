"""Exercise field validator branches."""

from custom_components.haeo.schema.fields import AnyKW


def test_power_flow_field_validators_allow_positive_values() -> None:
    """AnyKW should coerce and validate floats."""

    validator = AnyKW()
    schema = validator.create_schema()

    assert schema(1.5) == 1.5


def test_power_flow_field_validators_allow_negative_values() -> None:
    """AnyKW should allow negative values for bidirectional power flow."""

    validator = AnyKW()
    schema = validator.create_schema()

    assert schema(-5.0) == -5.0
