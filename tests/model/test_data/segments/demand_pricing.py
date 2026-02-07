"""Demand pricing segment scenarios."""

from datetime import timezone

import numpy as np

from custom_components.haeo.model.elements.segments import DemandPricingSegment

from ..segment_types import SegmentScenario

SCENARIOS: list[SegmentScenario] = [
    {
        "description": "Demand pricing adds peak cost",
        "factory": DemandPricingSegment,
        "spec": {
            "segment_type": "demand_pricing",
            "demand_price_source_target": 10.0,
            "demand_block_hours": 1.0,
        },
        "periods": np.array([1.0]),
        "inputs": {
            "power_in_st": [5.0],
            "power_in_ts": [0.0],
            "minimize_cost": True,
        },
        "expected_outputs": {"objective_value": 50.0},
    },
    {
        "description": "Demand pricing includes prior energy in first block",
        "factory": DemandPricingSegment,
        "spec": {
            "segment_type": "demand_pricing",
            "demand_price_source_target": 10.0,
            "demand_current_energy_source_target": 1.0,
            "demand_block_hours": 1.0,
        },
        "periods": np.array([1.0]),
        "inputs": {
            "power_in_st": [0.0],
            "power_in_ts": [0.0],
            "minimize_cost": True,
        },
        "expected_outputs": {"objective_value": 10.0},
    },
    {
        "description": "Demand pricing honors prior peak energy",
        "factory": DemandPricingSegment,
        "spec": {
            "segment_type": "demand_pricing",
            "demand_price_source_target": 10.0,
            "demand_peak_energy_source_target": 4.0,
            "demand_block_hours": 1.0,
        },
        "periods": np.array([1.0]),
        "inputs": {
            "power_in_st": [0.0],
            "power_in_ts": [0.0],
            "minimize_cost": True,
        },
        "expected_outputs": {"objective_value": 40.0},
    },
    {
        "description": "Demand pricing scales by block price weights",
        "factory": DemandPricingSegment,
        "spec": {
            "segment_type": "demand_pricing",
            "demand_price_source_target": np.array([10.0, 0.0, 10.0, 10.0]),
            "demand_block_hours": 0.5,
        },
        "periods": np.array([0.25, 0.25, 0.25, 0.25]),
        "inputs": {
            "power_in_st": [10.0, 0.0, 1.0, 1.0],
            "power_in_ts": [0.0, 0.0, 0.0, 0.0],
            "minimize_cost": True,
        },
        "expected_outputs": {"objective_value": 25.0},
    },
    {
        "description": "Demand pricing aligns to wall-clock blocks",
        "factory": DemandPricingSegment,
        "spec": {
            "segment_type": "demand_pricing",
            "demand_price_source_target": 1.0,
            "demand_block_hours": 0.5,
        },
        "periods": np.array([0.5, 0.5]),
        "period_start_time": 900.0,
        "period_start_timezone": timezone.utc,
        "inputs": {
            "power_in_st": [10.0, 0.0],
            "power_in_ts": [0.0, 0.0],
            "minimize_cost": True,
        },
        "expected_outputs": {"objective_value": 5.0},
    },
]

__all__ = ["SCENARIOS"]
