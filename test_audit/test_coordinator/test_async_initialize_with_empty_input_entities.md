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
  nodeid: tests/test_coordinator.py::test_async_initialize_with_empty_input_entities
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_initialize_with_empty_input_entities
  fixtures: []
  markers: []
notes:
  behavior: Raises UpdateFailed when initialization runs with empty inputs.
  redundancy: Covers empty-input error path.
  decision_rationale: Keep. Initialization error handling matters.
---

# Behavior summary

Initialization fails cleanly when no input entities are available.

# Redundancy / overlap

Distinct from other runtime-data missing guards.

# Decision rationale

Keep. Protects against invalid startup state.

# Fixtures / setup

Mocks empty inputs.

# Next actions

None.
