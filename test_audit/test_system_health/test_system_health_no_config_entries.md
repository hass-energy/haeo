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
  nodeid: tests/test_system_health.py::test_system_health_no_config_entries
  source_file: tests/test_system_health.py
  test_class: ''
  test_function: test_system_health_no_config_entries
  fixtures: []
  markers: []
notes:
  behavior: Returns a no_config_entries status when there are no entries.
  redundancy: Base case for system health output.
  decision_rationale: Keep. Validates empty-state behavior.
---

# Behavior summary

Calls `async_system_health_info` with no entries and asserts the status response.

# Redundancy / overlap

No overlap with coordinator state tests.

# Decision rationale

Keep. Ensures correct empty-state status.

# Fixtures / setup

Uses `hass`.

# Next actions

None.
