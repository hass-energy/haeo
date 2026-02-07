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
  nodeid: tests/entities/test_haeo_switch.py::test_handle_horizon_change_editable_updates_forecast
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_handle_horizon_change_editable_updates_forecast
  fixtures: []
  markers: []
notes:
  behavior: Editable horizon change updates forecast values.
  redundancy: Core horizon update path.
  decision_rationale: Keep. Ensures forecast refresh.
---

# Behavior summary

Horizon change rebuilds editable forecast.

# Redundancy / overlap

Complementary to timestamp write regression test.

# Decision rationale

Keep. Validates forecast refresh.

# Fixtures / setup

Adds entity to platform.

# Next actions

None.
