"""Test data and validation for energy_storage flow configuration."""

from custom_components.haeo.const import CONF_NAME
from custom_components.haeo.elements.energy_storage import CONF_CAPACITY, CONF_INITIAL_CHARGE

# Test data for energy_storage flow
VALID_DATA = [
    {
        "description": "Basic energy storage configuration",
        "config": {
            CONF_NAME: "Test Storage",
            CONF_CAPACITY: ["sensor.energy_capacity"],
            CONF_INITIAL_CHARGE: ["sensor.energy_charge"],
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty name should fail validation",
        "config": {
            CONF_NAME: "",
            CONF_CAPACITY: ["sensor.energy_capacity"],
            CONF_INITIAL_CHARGE: ["sensor.energy_charge"],
        },
        "error": "cannot be empty",
    },
]
