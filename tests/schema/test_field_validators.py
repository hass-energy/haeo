"""Exercise field validator branches."""

from custom_components.haeo.schema.fields import PowerFlowFieldMeta


def test_power_flow_field_meta_validators_allow_positive_values() -> None:
    """PowerFlowFieldMeta should coerce and validate floats."""

    meta = PowerFlowFieldMeta()
    validator = meta.create_schema()

    assert validator(1.5) == 1.5
