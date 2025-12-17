"""Input entities for HAEO runtime configuration.

Input entities are created from element configuration and manage their own state
independently of the optimization coordinator. They support two modes:

- **Editable**: User can change the value via the UI or automations.
  The value is persisted and used for subsequent optimizations.

- **Driven**: The value mirrors an external Home Assistant entity.
  Changes to the external entity are reflected in this entity.
"""

from .mode import InputMode
from .number import HaeoInputNumber
from .switch import HaeoInputSwitch

__all__ = [
    "HaeoInputNumber",
    "HaeoInputSwitch",
    "InputMode",
]
