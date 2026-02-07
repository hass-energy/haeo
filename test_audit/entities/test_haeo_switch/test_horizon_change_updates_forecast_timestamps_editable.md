---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/entities/test_haeo_switch.py::test_horizon_change_updates_forecast_timestamps_editable
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_horizon_change_updates_forecast_timestamps_editable
  fixtures: []
  markers: []
notes:
  behavior: Editable horizon change writes updated forecast timestamps to HA.
  redundancy: Regression coverage for state writes.
  decision_rationale: Keep. Prevents regression in state updates.
---

# Behavior summary

Horizon change triggers state write with new timestamps.

# Redundancy / overlap

Specific regression scenario.

# Decision rationale

Keep. Ensures HA state is written.

# Fixtures / setup

Wraps async_write_ha_state to capture forecast.

# Next actions

None.
