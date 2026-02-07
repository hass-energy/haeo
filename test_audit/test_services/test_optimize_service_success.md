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
  nodeid: tests/test_services.py::test_optimize_service_success
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_optimize_service_success
  fixtures: []
  markers: []
notes:
  behavior: Invokes optimize service and triggers coordinator optimization.
  redundancy: Unique behavior for optimize service execution.
  decision_rationale: Keep. Validates optimize service action.
---

# Behavior summary

Calls optimize service and asserts coordinator optimize is invoked.

# Redundancy / overlap

No overlap with diagnostics service tests.

# Decision rationale

Keep. Core optimize service behavior.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator.

# Next actions

None.
