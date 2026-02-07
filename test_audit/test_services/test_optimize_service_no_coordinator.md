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
  nodeid: tests/test_services.py::test_optimize_service_no_coordinator
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_optimize_service_no_coordinator
  fixtures: []
  markers: []
notes:
  behavior: Loaded entry without coordinator yields config_entry_not_loaded.
  redundancy: Unique optimize-specific runtime state check.
  decision_rationale: Keep. Validates runtime precondition for optimize.
---

# Behavior summary

Asserts optimize service raises config_entry_not_loaded when coordinator is missing.

# Redundancy / overlap

No overlap with other service validation tests.

# Decision rationale

Keep. Optimizer requires a coordinator.

# Fixtures / setup

Uses Home Assistant fixtures and a loaded entry without coordinator.

# Next actions

None.
