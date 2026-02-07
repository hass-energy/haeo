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
  nodeid: tests/entities/test_haeo_horizon.py::test_native_value_is_start_time_iso
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_native_value_is_start_time_iso
  fixtures: []
  markers: []
notes:
  behavior: Native value is ISO-formatted start timestamp string.
  redundancy: Core state behavior.
  decision_rationale: Keep. Ensures native value formatting.
---

# Behavior summary

Native value is string ISO timestamp.

# Redundancy / overlap

Distinct from forecast attribute tests.

# Decision rationale

Keep. Prevents formatting regressions.

# Fixtures / setup

Uses horizon manager timestamps.

# Next actions

None.
