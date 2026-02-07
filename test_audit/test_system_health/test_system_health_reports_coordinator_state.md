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
  nodeid: tests/test_system_health.py::test_system_health_reports_coordinator_state
  source_file: tests/test_system_health.py
  test_class: ''
  test_function: test_system_health_reports_coordinator_state
  fixtures: []
  markers: []
notes:
  behavior: Reports coordinator status, cost, duration, time, output count, and total periods.
  redundancy: Main success-path coverage for system health output.
  decision_rationale: Keep. Validates detailed health reporting.
---

# Behavior summary

Creates a mock coordinator with outputs and asserts system health reports expected fields and values.

# Redundancy / overlap

No overlap with update_failed or uninitialized cases.

# Decision rationale

Keep. Ensures system health output is complete and accurate.

# Fixtures / setup

Uses `hass` and patches config entries.

# Next actions

None.
