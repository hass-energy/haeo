---
name: elements
description: Element type development across the schema, adapter, and flow packages — config fields, output sensors, model element construction, and the registries every element type must be added to. Element types are battery, battery_section, connection, grid, inverter, load, node, policy, and solar. Use when adding a new element type or changing an existing one's fields, sensors, or model elements.
---

# Elements layer development

The elements layer bridges Home Assistant configuration with the LP model layer.
Each element type is split across three packages: schema, adapter, and flow.

When modifying elements, ensure corresponding updates to:

- `docs/user-guide/elements/` for user-facing configuration
- `docs/modeling/device-layer/` for mathematical formulation
- Colocated `tests/` directories for element tests

## Element file locations

Each element type has files in three separate packages:

```
core/schema/elements/{type}.py     # ConfigSchema and ConfigData TypedDicts
core/adapters/elements/{type}.py   # model_elements(), outputs(), adapter instance
flows/elements/{type}.py           # Config subentry flow implementation
```

The `elements/` package holds shared infrastructure that works the same for every element type:

```
elements/
├── __init__.py          # Type unions, registries keyed by element type, config accessors
├── availability.py      # Generic schema-driven availability checking
├── field_hints.py       # Turns schema field hints into HA entity descriptions
├── field_schema.py      # Re-export of core.schema.field_schema
└── input_fields.py      # Input field metadata types
```

The adapter registry itself lives in `core/adapters/registry.py` and is re-exported from `elements/__init__.py`.

## Schema module (`core/schema/elements/{type}.py`)

Defines two parallel TypedDicts and the field metadata that drives the rest of the system:

- **`{Type}ConfigSchema`** — what Home Assistant stores.
    Values are `EntityValue | ConstantValue | NoneValue`.
- **`{Type}ConfigData`** — what the optimizer receives.
    The same fields carrying loaded values (`NDArray[np.floating[Any]] | float`).

Fields are `Annotated` with `SectionHints` mapping each field name to a `FieldHint`.
The hint is the single source of truth for units, direction, time-series behavior, and defaults:

```python
class GridConfigSchema(ConnectedCommonConfig):
    """Grid element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.GRID]
    power_limits: Annotated[
        PowerLimitsConfig,
        SectionHints(
            {
                CONF_MAX_POWER_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.POWER_LIMIT,
                    direction="+",
                    time_series=True,
                    default_mode="value",
                    default_value=100.0,
                ),
            }
        ),
    ]
```

Declare defaults on the `FieldHint`, never in a separate constant or a comment.
Reuse the shared field groups in `core/schema/sections/` rather than redeclaring common fields.

## Adapter module (`core/adapters/elements/{type}.py`)

The `ElementAdapter` protocol in `core/adapters/registry.py` requires:

- Attributes `element_type`, `advanced`, `connectivity`, `can_source`, `can_sink`
- `model_elements(config)` — transform loaded config into model element params
- `outputs(name, model_outputs, **kwargs)` — map model outputs to device outputs

Availability and input field derivation are deliberately **not** adapter methods.
`availability.py` and `input_fields.py` derive both generically from the schema, so every element type behaves identically.
When a per-element hook seems necessary for either, express the difference in the schema instead.

The module also declares the element's output and device name literals plus matching frozensets, and exposes a module-level `adapter` instance.

## Flow module (`flows/elements/{type}.py`)

A `ConfigSubentryFlow` subclass using `ElementFlowMixin`.
The element-specific part is `_get_sections()`; the rest is shared boilerplate driven by that sections tuple.

Defaults reach the form through `build_sectioned_choose_defaults()`, which reads them from the schema's field hints.
Do not hand-maintain a defaults dict in the flow.

## Registration touchpoints

Adding an element type means updating every registry that enumerates types explicitly.
Pyright catches most omissions; the parametrized tests catch the rest.

| File                                   | What to add                                                                                                                              |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `core/schema/elements/element_type.py` | `ElementType` enum member                                                                                                                |
| `core/schema/elements/{type}.py`       | `ELEMENT_TYPE`, `{Type}ConfigSchema`, `{Type}ConfigData`, `OPTIONAL_INPUT_FIELDS`                                                        |
| `core/schema/elements/__init__.py`     | Config schema and data unions, plus the schema-by-type mapping                                                                           |
| `core/adapters/elements/{type}.py`     | Output and device name literals, adapter class, `adapter` instance                                                                       |
| `core/adapters/registry.py`            | Entry in `ELEMENT_TYPES`                                                                                                                 |
| `elements/__init__.py`                 | `ElementOutputName` / `ElementDeviceName` unions, `ELEMENT_DEVICE_NAMES_BY_TYPE`, `ELEMENT_CONFIG_DATA`, `ELEMENT_OPTIONAL_INPUT_FIELDS` |
| `flows/elements/{type}.py`             | `{Type}SubentryFlowHandler`                                                                                                              |
| `flows/__init__.py`                    | Entry in the subentry flow handler map                                                                                                   |
| `translations/en.json`                 | Device, subentry, and entity strings for the new type and its outputs                                                                    |

Tests and documentation are part of the same change:

- Adapter tests in `core/adapters/elements/tests/`
- Flow tests in `flows/elements/tests/` and flow test data in `flows/tests/test_data/{type}.py`
- Model element cases in `core/model/tests/test_data/` if the element introduces one
- User guide in `docs/user-guide/elements/` and modeling docs in `docs/modeling/device-layer/`

The fastest way to find every touchpoint is to grep for an existing element of a similar shape:

```bash
grep -rln "ElementType.GRID\|GridConfigSchema\|GridConfigData\|GridSubentryFlowHandler\|grid_adapter" \
    custom_components/haeo --include="*.py"
```

Pick the closest analogue to copy: `grid` connects to one participant with directional pricing and power limits,
`load` and `solar` are single-direction elements driven by forecasts,
`battery` is stateful and expands into several model elements,
`node` and `connection` are advanced-mode topology primitives,
and `policy` has no physical model element at all.

## Working order

The registries reference each other, so this order keeps the type checker useful rather than drowning you in errors:

1. `ElementType` member and the schema module — nothing else compiles without them.
2. Adapter module and its registry entry.
    Run `uv run pyright` here; it names every union and mapping still missing the type.
3. Flow module and its handler map entry.
4. Translations for the device, subentry, and every new output.
5. Test data.
    The parametrized suites iterate the registry, so they start failing once step 2 lands and stay failing until the data exists.
6. User guide and modeling documentation.

Steps 4 through 6 are part of the change, not follow-up work, and CI checks all three.

Run `uv run check --fast` between steps and `uv run check` before finishing.
Pyright catches missing registry entries, the flow and adapter tests catch missing test data,
the output completeness test catches an output name declared but never produced,
and the translation tests catch strings missing for a registered type.
