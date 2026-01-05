"""Test data and factories for SchedulableLoad element."""

from custom_components.haeo.model.schedulable_load import SchedulableLoad

from .element_types import ElementTestCase

VALID_CASES: list[ElementTestCase] = [
    {
        "description": "Schedulable load starting at beginning of horizon",
        "factory": SchedulableLoad,
        "data": {
            "name": "load_start",
            "periods": [1.0, 1.0, 1.0, 1.0],
            "power": 2.0,
            "duration": 2.0,
            "earliest_start": 0.0,
            "latest_start": 0.0,  # Fixed at start
        },
        "inputs": {
            # Negative values = power flows INTO the load (load consumes)
            "power": [-2.0, -2.0, 0.0, 0.0],
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "schedulable_load_power_consumed": {
                "type": "power",
                "unit": "kW",
                "values": (2.0, 2.0, 0.0, 0.0),
            },
            "schedulable_load_start_time": {
                "type": "duration",
                "unit": "h",
                "values": (0.0,),
            },
            "schedulable_load_power_balance": {
                "type": "shadow_price",
                "unit": "$/kW",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_left_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_left_edge_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_right_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_right_edge_end": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_overlap_min": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_overlap_max": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_total_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_power_from_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_earliest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_latest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
        },
    },
    {
        "description": "Schedulable load starting at end of window",
        "factory": SchedulableLoad,
        "data": {
            "name": "load_end",
            "periods": [1.0, 1.0, 1.0, 1.0],
            "power": 2.0,
            "duration": 2.0,
            "earliest_start": 2.0,
            "latest_start": 2.0,  # Fixed at end
        },
        "inputs": {
            # Negative values = power flows INTO the load (load consumes)
            "power": [0.0, 0.0, -2.0, -2.0],
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "schedulable_load_power_consumed": {
                "type": "power",
                "unit": "kW",
                "values": (0.0, 0.0, 2.0, 2.0),
            },
            "schedulable_load_start_time": {
                "type": "duration",
                "unit": "h",
                "values": (2.0,),
            },
            "schedulable_load_power_balance": {
                "type": "shadow_price",
                "unit": "$/kW",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_left_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_left_edge_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_right_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_right_edge_end": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_overlap_min": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_overlap_max": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_total_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_power_from_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_earliest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_latest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
        },
    },
    {
        "description": "Schedulable load with fractional period overlap",
        "factory": SchedulableLoad,
        "data": {
            "name": "load_fractional",
            "periods": [1.0, 1.0, 1.0, 1.0],
            "power": 2.0,
            "duration": 1.5,
            "earliest_start": 0.5,
            "latest_start": 0.5,  # Fixed start time
        },
        "inputs": {
            # Start fixed at 0.5, run until 2.0
            # Period 0 (0-1): overlap 0.5h -> 1.0 kW average
            # Period 1 (1-2): overlap 1.0h -> 2.0 kW average
            # Negative values = power flows INTO the load
            "power": [-1.0, -2.0, 0.0, 0.0],
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "schedulable_load_power_consumed": {
                "type": "power",
                "unit": "kW",
                "values": (1.0, 2.0, 0.0, 0.0),
            },
            "schedulable_load_start_time": {
                "type": "duration",
                "unit": "h",
                "values": (0.5,),
            },
            "schedulable_load_power_balance": {
                "type": "shadow_price",
                "unit": "$/kW",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_left_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_left_edge_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_right_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_right_edge_end": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_overlap_min": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_overlap_max": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_total_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_power_from_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_earliest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_latest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
        },
    },
    {
        "description": "Schedulable load with variable period lengths",
        "factory": SchedulableLoad,
        "data": {
            "name": "load_variable",
            "periods": [0.5, 1.0, 0.5, 1.0],
            "power": 3.0,
            "duration": 1.0,
            "earliest_start": 0.5,
            "latest_start": 0.5,  # Fixed to start at 0.5
        },
        "inputs": {
            # Start at 0.5, run until 1.5
            # Period 0 (0-0.5): overlap 0h -> 0.0 kW
            # Period 1 (0.5-1.5): overlap 1.0h -> 3.0 kW
            # Negative values = power flows INTO the load
            "power": [0.0, -3.0, 0.0, 0.0],
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "schedulable_load_power_consumed": {
                "type": "power",
                "unit": "kW",
                "values": (0.0, 3.0, 0.0, 0.0),
            },
            "schedulable_load_start_time": {
                "type": "duration",
                "unit": "h",
                "values": (0.5,),
            },
            "schedulable_load_power_balance": {
                "type": "shadow_price",
                "unit": "$/kW",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_left_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_left_edge_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_right_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_right_edge_end": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_overlap_min": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_overlap_max": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_total_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_power_from_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0, 0.0, 0.0),
            },
            "schedulable_load_earliest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_latest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
        },
    },
    {
        "description": "Schedulable load with zero duration (instant)",
        "factory": SchedulableLoad,
        "data": {
            "name": "load_zero_duration",
            "periods": [1.0, 1.0],
            "power": 5.0,
            "duration": 0.0,
            "earliest_start": 0.0,
            "latest_start": 2.0,
        },
        "inputs": {
            "power": [None, None],
            "input_cost": 0.0,
            "output_cost": 0.0,
        },
        "expected_outputs": {
            "schedulable_load_power_consumed": {
                "type": "power",
                "unit": "kW",
                "values": (0.0, 0.0),
            },
            "schedulable_load_start_time": {
                "type": "duration",
                "unit": "h",
                "values": (0.0,),
            },
            "schedulable_load_power_balance": {
                "type": "shadow_price",
                "unit": "$/kW",
                "values": (0.0, 0.0),
            },
            "schedulable_load_left_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0),
            },
            "schedulable_load_left_edge_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0),
            },
            "schedulable_load_right_edge_boundary": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0),
            },
            "schedulable_load_right_edge_end": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0),
            },
            "schedulable_load_overlap_min": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0),
            },
            "schedulable_load_overlap_max": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0),
            },
            "schedulable_load_total_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_power_from_overlap": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0, 0.0),
            },
            "schedulable_load_earliest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
            "schedulable_load_latest_start": {
                "type": "shadow_price",
                "unit": "$/kWh",
                "values": (0.0,),
            },
        },
    },
]

INVALID_CASES: list[ElementTestCase] = [
    {
        "description": "Schedulable load with negative power",
        "factory": SchedulableLoad,
        "data": {
            "name": "load_negative_power",
            "periods": [1.0, 1.0],
            "power": -2.0,
            "duration": 1.0,
            "earliest_start": 0.0,
            "latest_start": 1.0,
        },
        "expected_error": r"power must be non-negative",
    },
    {
        "description": "Schedulable load with negative duration",
        "factory": SchedulableLoad,
        "data": {
            "name": "load_negative_duration",
            "periods": [1.0, 1.0],
            "power": 2.0,
            "duration": -1.0,
            "earliest_start": 0.0,
            "latest_start": 1.0,
        },
        "expected_error": r"duration must be non-negative",
    },
    {
        "description": "Schedulable load with negative earliest_start",
        "factory": SchedulableLoad,
        "data": {
            "name": "load_negative_earliest",
            "periods": [1.0, 1.0],
            "power": 2.0,
            "duration": 1.0,
            "earliest_start": -1.0,
            "latest_start": 1.0,
        },
        "expected_error": r"earliest_start must be non-negative",
    },
    {
        "description": "Schedulable load with latest_start < earliest_start",
        "factory": SchedulableLoad,
        "data": {
            "name": "load_invalid_window",
            "periods": [1.0, 1.0],
            "power": 2.0,
            "duration": 1.0,
            "earliest_start": 1.5,
            "latest_start": 0.5,
        },
        "expected_error": r"latest_start \(0\.5\) must be >= earliest_start \(1\.5\)",
    },
]
