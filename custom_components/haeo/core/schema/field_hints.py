"""Declarative hints for input fields.

This module provides an HA-free way to define metadata for input fields
alongside their schema definitions. The elements layer will transform these
hints into full HA InputFieldInfo and EntityDescription objects.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, Literal, NotRequired, Required, get_args, get_origin, get_type_hints

from custom_components.haeo.core.model.const import OutputType

type CalendarProjection = Literal["window_active", "window_starts", "event_opens", "event_due"]

# Projections with one value per horizon boundary rather than per period
_BOUNDARY_PROJECTIONS: frozenset[CalendarProjection] = frozenset({"window_starts", "event_opens", "event_due"})


@dataclass(frozen=True, slots=True)
class CalendarFieldHint:
    """How an input resolves its values from the events of a calendar entity.

    Attributes:
        projection: Which series the input takes from the events:
            - 'window_active': per period, 1.0 inside a window. Every event is a
              window, including one whose text holds no value, which is due
              nothing. Overlapping events merge into one window and events that
              only touch stay separate.
            - 'window_starts': per boundary, 1.0 where a window starts after the
              horizon start. A window open at the horizon start does not start.
            - 'event_opens': per boundary, the summed values of the events
              starting there. An event open at the horizon start opens at
              boundary 0.
            - 'event_due': per boundary, the summed values of the events
              ending there. An event running past the horizon is due at its
              end.

            Each event's value is a number with its unit, such as "40 km",
            converted to the input's unit.

    """

    projection: CalendarProjection


@dataclass(frozen=True, slots=True)
class MeterFieldHint:
    """How an input reads a meter: a running total, such as an energy sensor that only counts up.

    Attributes:
        since: The calendar field, in the same section, whose window open at
            the horizon start sets the meter's zero point. The amount the
            meter rose since that window started loads beside the field.

    """

    since: str


@dataclass(frozen=True, slots=True)
class FieldHint:
    """Metadata for a config field that becomes an input entity.

    Attributes:
        output_type: Semantic type of the output (POWER, ENERGY, etc.).
            Drives default HA unit, device_class, min, max, and step values.
        direction: "+" or "-" for power direction attributes.
        time_series: Whether this field is time series (list) or scalar.
        boundaries: Whether time series values are at boundaries (n+1) vs intervals (n).
        min_value: Override default min value for the OutputType.
        max_value: Override default max value for the OutputType.
        step: Override default step value for the OutputType.
        default_mode: Controls config flow pre-selection ('entity' or 'value').
        default_value: Value to pre-fill when default_mode='value'.
        force_required: Force value to be required, overriding schema optionality.
        calendar: When set, the input resolves its values from the events of the
            calendars it reads.
        outputs: When set, the field feeds these inputs, keyed by their loaded
            field names, instead of being an input itself. The calendars it
            reads can so feed several inputs, each with its own entity.
        meter: When set, the input reads meters, and the amount they rose
            since a calendar window started loads beside it.

    """

    output_type: OutputType
    direction: str | None = None
    time_series: bool = False
    boundaries: bool = False
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    default_mode: Literal["entity", "value"] | None = None
    default_value: float | bool | None = None
    force_required: bool | None = None
    calendar: CalendarFieldHint | None = None
    outputs: Mapping[str, FieldHint] | None = None
    meter: MeterFieldHint | None = None


def calendar_input(output_type: OutputType, projection: CalendarProjection) -> FieldHint:
    """Return the hint for an input resolved from calendar events.

    Calendar inputs are always time series, at boundaries for the projections
    that place values there.
    """
    return FieldHint(
        output_type=output_type,
        time_series=True,
        boundaries=projection in _BOUNDARY_PROJECTIONS,
        calendar=CalendarFieldHint(projection=projection),
    )


def field_inputs(field_name: str, hint: FieldHint) -> list[tuple[str, FieldHint]]:
    """Return the inputs a config field feeds, as (loaded field name, hint): its outputs, or itself."""
    return list(hint.outputs.items()) if hint.outputs else [(field_name, hint)]


@dataclass(frozen=True, slots=True)
class SurfacedPriceHint:
    """Metadata for a pricing field surfaced from policy rules onto an element form.

    These fields appear on the element's config flow but are stored as
    policy rules rather than in the element's own config data.

    Attributes:
        hint: The field hint defining output type, defaults, and constraints.
        source_is_wildcard: If True, the rule pattern is ``* → element``.
            If False, the pattern is ``element → *``.
        negate: If True, the surfaced value is the negation of the stored policy
            price. The element form and surfaced entities show the running
            (positive) value while the policy rule stores its negative.

    """

    hint: FieldHint
    source_is_wildcard: bool
    negate: bool = False


@dataclass(frozen=True, slots=True)
class SectionHints:
    """Wrapper for field hints to use in Annotated metadata."""

    fields: dict[str, FieldHint]


@dataclass(frozen=True, slots=True)
class ListFieldHints:
    """Wrapper for field hints within items of a list config field.

    Used with ``Annotated`` on list-typed TypedDict fields to declare that
    each item in the list has configurable input fields.  The extraction
    pipeline reads these hints and generates per-item input field definitions
    at runtime based on the actual config data.

    Attributes:
        fields: Mapping of field name to ``FieldHint`` for each item field
            that should become an input entity.

    Example::

        class PolicyConfigSchema(TypedDict):
            rules: Annotated[list[PolicyRuleConfig], ListFieldHints(
                fields={"price": FieldHint(output_type=OutputType.PRICE, time_series=True)},
            )]

    """

    fields: dict[str, FieldHint]


def extract_field_hints(schema_cls: type) -> dict[str, dict[str, FieldHint]]:
    """Extract declarative field hints from a TypedDict's Annotated metadata."""
    hints = get_type_hints(schema_cls, include_extras=True)
    result: dict[str, dict[str, FieldHint]] = {}

    for section_key, section_type in hints.items():
        origin = get_origin(section_type)
        if origin in (Required, NotRequired):
            unwrapped_type = get_args(section_type)[0]
            origin = get_origin(unwrapped_type)
        else:
            unwrapped_type = section_type

        if origin is Annotated:
            for arg in get_args(unwrapped_type)[1:]:
                if isinstance(arg, SectionHints):
                    result[section_key] = arg.fields
                    break

    return result


def extract_list_field_hints(schema_cls: type) -> dict[str, ListFieldHints]:
    """Extract list field hints from a TypedDict's Annotated metadata.

    Finds fields annotated with ``ListFieldHints`` and returns them keyed
    by their field name.  This is the list-based counterpart to
    ``extract_field_hints`` which handles section-based hints.
    """
    hints = get_type_hints(schema_cls, include_extras=True)
    result: dict[str, ListFieldHints] = {}

    for field_key, field_type in hints.items():
        origin = get_origin(field_type)
        if origin in (Required, NotRequired):
            unwrapped_type = get_args(field_type)[0]
            origin = get_origin(unwrapped_type)
        else:
            unwrapped_type = field_type

        if origin is Annotated:
            for arg in get_args(unwrapped_type)[1:]:
                if isinstance(arg, ListFieldHints):
                    result[field_key] = arg
                    break

    return result
