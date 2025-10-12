# Network Model API

The network model represents the complete energy system for optimization.

## Network Class

Main network class that:

- Contains all entities (batteries, grids, loads, etc.)
- Manages connections between entities
- Builds the linear programming problem
- Runs the optimization solver

### Location

`custom_components/haeo/model/network.py`

### Key Methods

#### `add(element_type, name, **kwargs)`

Adds an entity to the network.

#### `connect(source, target, min_power, max_power)`

Creates a connection between two entities.

#### `optimize()`

Runs the optimization solver and returns results.

### Usage

```python
network = Network(period=1 / 12, n_periods=576)  # 5min periods, 48 hours
network.add("battery", "main_battery", capacity=15.0)
network.add("grid", "main_grid")
network.connect("main_battery", "main_grid")
result = network.optimize()
```

## Related Models

- [Battery Model](battery.md)
- [Grid Model](grid.md)
- [Load Models](loads.md)
- [Photovoltaics Model](photovoltaics.md)
- [Connection Model](connections.md)

See `custom_components/haeo/model/` for all model implementations.
