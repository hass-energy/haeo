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
  nodeid: tests/entities/test_haeo_number.py::test_horizon_change_updates_forecast_timestamps_driven
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_horizon_change_updates_forecast_timestamps_driven
  fixtures: []
  markers: []
notes:
  behavior: Driven horizon change writes updated forecast timestamps to HA.
  redundancy: Regression coverage for state writes.
  decision_rationale: Keep. Prevents regressions in driven updates.
---

# Behavior summary

Horizon change triggers state write with updated timestamps in driven mode.

# Redundancy / overlap

More assertive than basic reload test.

# Decision rationale

Keep. Ensures HA state is written.

# Fixtures / setup

Mocks loader and wraps async_write_ha_state.

# Next actions

None.
