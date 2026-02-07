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
  nodeid: tests/test_coordinator.py::test_load_element_config_raises_without_runtime_data
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_load_element_config_raises_without_runtime_data
  fixtures: []
  markers: []
notes:
  behavior: Raises when element config load runs without runtime data.
  redundancy: Related to other runtime data guards.
  decision_rationale: Keep. Enforces runtime data prerequisite.
---

# Behavior summary

Element config load fails when runtime data is missing.

# Redundancy / overlap

One of several runtime data guard cases.

# Decision rationale

Keep. Ensures missing runtime data is handled.

# Fixtures / setup

Mocks missing runtime data.

# Next actions

None.
