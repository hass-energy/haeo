"""Input mode for HAEO input entities."""


class InputMode:
    """Operating mode for input entities.

    DRIVEN: The entity mirrors an external Home Assistant entity's value.
            Changes to the external entity are reflected in this entity.
            User cannot change the value directly.

    EDITABLE: User can change the value via the UI or automations.
              The value is persisted and used for subsequent optimizations.
    """

    DRIVEN = "driven"
    EDITABLE = "editable"


__all__ = ["InputMode"]
