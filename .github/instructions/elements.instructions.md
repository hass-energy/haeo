---
applyTo: custom_components/haeo/elements/**
description: Elements layer development standards
globs: [custom_components/haeo/elements/**]
alwaysApply: false
---

# Elements layer development

The elements layer bridges Home Assistant configuration with the LP model layer.
Element types are registered in the `ELEMENT_TYPES` registry which defines the schema, data, adapter, and extractor for each type.

When modifying elements, ensure corresponding updates to:

- `docs/user-guide/elements/` for user-facing configuration
- `docs/modeling/device-layer/` for mathematical formulation

## Element pattern

Each element type follows a consistent pattern:

- **Schema TypedDict**: Defines UI configuration fields with entity IDs
- **Data TypedDict**: Defines loaded values after sensor data extraction
- **Adapter function**: Creates model layer elements from loaded data
- **Extractor function**: Converts optimization results to sensor data

## Data loading

- Field types use the composable metadata system (Validator, LoaderMeta, Default) defined in `schema/`
- Loaders handle sensor data extraction and constant value conversion
- Data availability is validated during config flow via `evaluate_network_connectivity()`

## Model creation

- Adapter functions receive Data mode TypedDict with loaded values
- Create model elements using kW/kWh/hours units (see [units](../../docs/developer-guide/units.md))
- Map HA configuration fields to model parameters

## Result extraction

- Extractor functions receive optimization results and return sensor data
- Use the output type system for consistent sensor creation
- Results are keyed by output name for sensor lookup

## Sensor patterns

- Use generic property detection instead of element type checking
- Use translation keys for sensor names (see translations.instructions.md)
- Set appropriate entity categories (e.g., DIAGNOSTIC for internal values)

## Adding new element types

1. Define Schema and Data TypedDicts with Annotated field types
2. Implement adapter function to create model elements
3. Implement extractor function to convert results to sensor data
4. Register in `ELEMENT_TYPES` with schema, data, defaults, adapter, and extractor
5. Add translations in `translations/en.json`
6. Document in `docs/user-guide/elements/` and `docs/modeling/device-layer/`
