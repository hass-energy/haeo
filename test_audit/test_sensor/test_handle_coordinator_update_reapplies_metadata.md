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
  nodeid: tests/test_sensor.py::test_handle_coordinator_update_reapplies_metadata
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_handle_coordinator_update_reapplies_metadata
  fixtures: []
  markers: []
notes:
  behavior: Reapplies metadata and forecast attributes on coordinator update.
  redundancy: Distinct from empty-data handling and percentage scaling.
  decision_rationale: Keep. Validates update behavior and copy semantics.
---

# Behavior summary

On update, refreshes native values, metadata, and forecast attributes with proper copying.

# Redundancy / overlap

No overlap with scaling or empty-data tests.

# Decision rationale

Keep. Core update behavior.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator data.

# Next actions

None.
