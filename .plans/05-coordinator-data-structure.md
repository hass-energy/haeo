# Phase 5: Update CoordinatorData Structure

## Goal

Change `CoordinatorData` to cleanly separate inputs from outputs per element. This provides clear structure for sensors and diagnostics.

## Prerequisites

- Phase 4 complete (echoed inputs removed from outputs)

## Deliverables

1. Updated `coordinator/network_coordinator.py` - New data structure
2. Updated `sensors/sensor.py` - Navigate new structure
3. Updated `diagnostics.py` - Use new structure

## New Data Structure

### Current Structure

```python
type SubentryDevices = dict[ElementDeviceName, dict[OutputName, CoordinatorOutput]]
type CoordinatorData = dict[str, SubentryDevices]

# Access: data[element_name][device_name][output_name]
```

### New Structure

```python
class ElementData(TypedDict):
    """Data for a single element."""

    inputs: ElementConfigData  # Loaded config values
    outputs: SubentryDevices  # Optimization results
    forecast_timestamps: tuple[float, ...]


class CoordinatorData(TypedDict):
    """Coordinator data with clear input/output separation."""

    elements: dict[str, ElementData]  # keyed by element name
    hub_outputs: SubentryDevices  # Network-level outputs (cost, status, duration)


# Access outputs: data["elements"][element_name]["outputs"][device_name][output_name]
# Access inputs: data["elements"][element_name]["inputs"][field_name]
```

## Implementation Details

### 1. Define New Types

```python
# In coordinator/network_coordinator.py


class ElementData(TypedDict):
    """Data structure for a single element's inputs and outputs.

    Attributes:
        inputs: Loaded configuration with resolved sensor/forecast values
        outputs: Sensor outputs grouped by device and output name
        forecast_timestamps: Timestamps for forecast periods
    """

    inputs: ElementConfigData
    outputs: SubentryDevices
    forecast_timestamps: tuple[float, ...]


class CoordinatorData(TypedDict):
    """Data structure returned by the coordinator update cycle.

    Separates element data (per-subentry) from hub-level outputs.
    """

    elements: dict[str, ElementData]
    hub_outputs: SubentryDevices
```

### 2. Update \_async_update_data Return

```python
async def _async_update_data(self) -> CoordinatorData:
    """Run optimization cycle."""

    # ... optimization logic ...

    # Build elements dict
    elements: dict[str, ElementData] = {}

    for element_name, element_config in loaded_configs.items():
        # Get outputs for this element
        outputs_fn = ELEMENT_TYPES[element_config["element_type"]].outputs
        adapter_outputs = outputs_fn(element_name, model_outputs, element_config)

        # Process outputs into SubentryDevices format
        subentry_devices: SubentryDevices = {}
        for device_name, device_outputs in adapter_outputs.items():
            subentry_devices[device_name] = {
                name: _build_coordinator_output(name, data, forecast_timestamps)
                for name, data in device_outputs.items()
            }

        elements[element_name] = ElementData(
            inputs=element_config,
            outputs=subentry_devices,
            forecast_timestamps=forecast_timestamps,
        )

    # Hub-level outputs
    hub_outputs: SubentryDevices = {
        ELEMENT_TYPE_NETWORK: {
            OUTPUT_NAME_OPTIMIZATION_COST: _build_coordinator_output(...),
            OUTPUT_NAME_OPTIMIZATION_STATUS: _build_coordinator_output(...),
            OUTPUT_NAME_OPTIMIZATION_DURATION: _build_coordinator_output(...),
        }
    }

    return CoordinatorData(
        elements=elements,
        hub_outputs=hub_outputs,
    )
```

### 3. Update Sensor Platform

```python
# In sensors/sensor.py


def _handle_coordinator_update(self) -> None:
    """Update sensor from coordinator data."""
    if not self.coordinator.data:
        return

    # Navigate new structure
    elements = self.coordinator.data.get("elements", {})
    element_data = elements.get(self._subentry_key)

    if element_data is None:
        # Try hub outputs for network-level sensors
        hub_outputs = self.coordinator.data.get("hub_outputs", {})
        outputs = hub_outputs.get(self._device_key, {})
    else:
        outputs = element_data.get("outputs", {}).get(self._device_key, {})

    output_data = outputs.get(self._output_name)
    if output_data:
        self._apply_output(output_data)
```

### 4. Update Diagnostics

```python
# In diagnostics.py


async def async_get_config_entry_diagnostics(hass, entry):
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.network_coordinator

    diag = {
        "config": {...},
        "participants": {},
        "outputs": {},
    }

    if coordinator.data:
        # Include inputs per element
        for name, element_data in coordinator.data["elements"].items():
            diag["participants"][name] = {
                "inputs": dict(element_data["inputs"]),
                "forecast_timestamps": element_data["forecast_timestamps"],
            }

        # Include hub outputs
        diag["outputs"]["hub"] = _serialize_outputs(coordinator.data["hub_outputs"])

    return diag
```

### 5. Update Tests

All tests that access coordinator.data need updating:

```python
# Before:
result[element_name][device_name][output_name]

# After:
result["elements"][element_name]["outputs"][device_name][output_name]
result["elements"][element_name]["inputs"][field_name]
result["hub_outputs"][device_name][output_name]
```

## Migration Checklist

Files to update:

- [ ] `coordinator/network_coordinator.py` - New structure definition and building
- [ ] `sensors/sensor.py` - Navigate new structure
- [ ] `sensors/__init__.py` - May need updates for entity setup
- [ ] `diagnostics.py` - Use new structure
- [ ] `tests/test_coordinator.py` - Update data access patterns
- [ ] `tests/test_sensor.py` - Update data access patterns
- [ ] `tests/test_diagnostics.py` - Update expectations

## Testing Considerations

- Verify all sensors still receive correct data
- Verify diagnostics output is complete
- Verify visualization tools work with new structure

## Acceptance Criteria

1. CoordinatorData clearly separates inputs from outputs
2. All sensors navigate new structure correctly
3. Diagnostics include both inputs and outputs
4. Tests updated and passing
5. No regression in functionality

## Benefits of New Structure

1. **Clarity**: Obvious what's an input vs output
2. **Debugging**: Easy to see what values were used for optimization
3. **Future Features**: Can add input sensors or history tracking
4. **Clean API**: Consumers know where to find what they need
