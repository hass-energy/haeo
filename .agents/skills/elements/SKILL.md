---
name: elements
description: Element type development for every type registered in ElementType — the schema module in core/schema/elements/, the adapter in core/adapters/elements/, the subentry flow in flows/elements/, config fields and field hints, output sensors and devices, model element construction, and the registries every element type must join. Use when adding a new element type, or changing an existing one's config fields, sensors, devices, or the model elements it builds.
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
├── __init__.py          # Output and device name unions, config accessors, input field lookups
├── field_hints.py       # Turns schema field hints into HA entity descriptions
└── input_fields.py      # Input field metadata types, including FieldSchemaInfo
```

The adapter registry `ELEMENT_TYPES` lives in `core/adapters/registry.py`.

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

Whether a field is optional comes from the TypedDict itself: mark it `NotRequired`.
`get_input_field_schema_info()` in `elements/__init__.py` reads that into `FieldSchemaInfo`, so there is no separate list of optional fields to keep in step.

A schema module may also export hooks that only some element types need.
Each is registered in a mapping in `core/schema/elements/__init__.py`, and code looks the type up there rather than naming it:

- `SURFACED_PRICE_HINTS` go in `ELEMENT_SURFACED_PRICE_HINTS` when the element's form shows policy pricing fields.
    The element's flow must list each surfaced field in one of its `sections`.
- `map_references` goes in `ELEMENT_REFERENCE_MAPPERS` when the config lists other elements, so a renamed element is renamed in it and a deleted one dropped.
    Connection targets need no mapper; they are renamed wherever they appear.

`is_element_config_schema()` in `core/schema/elements/conformance.py` checks a stored mapping against the schema registered for its type.

## Adapter module (`core/adapters/elements/{type}.py`)

The `ElementAdapter` protocol in `core/adapters/registry.py` requires:

- Attributes `element_type`, `advanced`, `connectivity`, `can_source`, `can_sink`, `switchboard`, `buffer_roles`, and `device_names`
- `model_elements(config)` — transform loaded config into model element params
- `outputs(name, model_outputs, **kwargs)` — map model outputs to device outputs

Shared code branches on these attributes, never on the element type.
An adapter whose elements choose in their config whether they produce or consume power also implements `ConfiguredRolesAdapter.roles(config)`.
`ELEMENT_DEVICE_NAMES_BY_TYPE` in `elements/__init__.py` is built from each adapter's `device_names`.

Availability and input field derivation are deliberately **not** adapter methods.
Input stores decide availability field by field, and `input_fields.py` derives input fields generically from the schema, so every element type behaves identically.
When a per-element hook seems necessary for either, express the difference in the schema instead.

The module also declares the element's output and device name literals plus matching frozensets, and exposes a module-level `adapter` instance.

An adapter builds configs for the model element types registered in `ELEMENTS` (`core/model/elements/__init__.py`).
When a new model element reads other elements' flows, give its `ElementSpec` an `arguments` hook that resolves the elements it names; it is added after the connections it reads because it is neither a network element nor a connection, and the network builder needs no change.

## Flow module (`flows/elements/{type}.py`)

A subclass of `ElementSubentryFlow` (`flows/element_flow.py`) that declares `element_type` and `sections` as class attributes.
Most flows subclass `SectionedElementSubentryFlow` (`flows/sectioned_flow.py`), which drives the form, validation, surfaced pricing fields, and saving from those attributes, or `ConnectedElementSubentryFlow` (`flows/connected_flow.py`) when the element connects to one other element.
Build sections from the helpers in `flows/sections/`.

Defaults reach the form through `build_sectioned_choose_defaults()`, which reads them from the schema's field hints.
Do not hand-maintain a defaults dict in the flow.

## Registration touchpoints

Adding an element type means updating every registry that enumerates types explicitly.
Pyright catches most omissions; the parametrized tests catch the rest.

| File                                   | What to add                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------ |
| `core/schema/elements/element_type.py` | `ElementType` enum member                                                            |
| `core/schema/elements/{type}.py`       | `ELEMENT_TYPE`, `{Type}ConfigSchema`, `{Type}ConfigData`, and any optional hooks     |
| `core/schema/elements/__init__.py`     | Schema and data unions, `ELEMENT_CONFIG_SCHEMAS`, and the hook mappings it needs     |
| `core/adapters/elements/{type}.py`     | Output and device name literals, adapter class, `adapter` instance                   |
| `core/adapters/registry.py`            | Entry in `ELEMENT_TYPES`                                                             |
| `elements/__init__.py`                 | `ElementOutputName` / `ElementDeviceName` unions and the output and device name sets |
| `flows/elements/{type}.py`             | `{Type}SubentryFlowHandler`                                                          |
| `flows/__init__.py`                    | Entry in `get_element_flow_classes()`                                                |
| `translations/en.json`                 | Device, subentry, and entity strings for the new type and its outputs                |

Tests and documentation are part of the same change:

- Adapter mapping cases in `core/adapters/elements/tests/test_data/{type}.py`, defining `CREATE_CASES` and `OUTPUTS_CASES`.
    The suite imports one module per type registered in `ELEMENT_TYPES`, so a missing module fails collection.
- Flow test data in `flows/tests/test_data/{type}.py`.
    Its `VALID_DATA` configs are in the shape the subentry stores, and the schema tests in `elements/tests/` validate them against the registered schema too.
- Flow tests in `flows/elements/tests/` for behavior specific to the type
- Model element cases in `core/model/tests/test_data/` if the element introduces a model element
- User guide in `docs/user-guide/elements/` and modeling docs in `docs/modeling/device-layer/`

The fastest way to find every touchpoint is to grep for an existing element of a similar shape:

```bash
grep -rln "ElementType.GRID\|GridConfigSchema\|GridConfigData\|GridSubentryFlowHandler\|grid_adapter" \
    custom_components/haeo --include="*.py"
```

Pick the closest analogue to copy by comparing adapter attributes such as `connectivity`, `advanced`, and `buffer_roles`, and the model elements each adapter's `model_elements()` builds.

## Working order

The registries reference each other, so this order keeps the type checker useful rather than drowning you in errors:

1. `ElementType` member and the schema module — nothing else compiles without them.
2. Adapter module and its registry entry.
    Run `uv run pyright` here; it names every union and mapping still missing the type.
3. Flow module and its entry in `get_element_flow_classes()`.
4. Translations for the device, subentry, and every new output.
5. Test data.
    The parametrized suites iterate the registry, so they start failing once step 2 lands and stay failing until the data exists.
6. User guide and modeling documentation.

Steps 4 through 6 are part of the change, not follow-up work, and CI checks all three.

Run `uv run check --fast` between steps and `uv run check` before finishing.
Pyright catches missing registry entries, the flow and adapter tests catch missing test data,
the output completeness test catches an output name declared but never produced,
and the translation tests catch strings missing or unused for a registered type.
