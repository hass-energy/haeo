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
  nodeid: tests/test_system_health.py::test_system_health_detects_failed_updates
  source_file: tests/test_system_health.py
  test_class: ''
  test_function: test_system_health_detects_failed_updates
  fixtures: []
  markers: []
notes:
  behavior: Reports update_failed when coordinator last update failed.
  redundancy: Distinct failure-path coverage.
  decision_rationale: Keep. Validates failed update status reporting.
---

# Behavior summary

Mocks a coordinator with failed update and asserts system health reports update_failed and zero outputs.

# Redundancy / overlap

No overlap with success or uninitialized cases.

# Decision rationale

Keep. Failure-state reporting is required.

# Fixtures / setup

Uses `hass` and patches config entries.

# Next actions

None.
