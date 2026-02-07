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
  nodeid: tests/test_coordinator.py::test_load_from_input_entities_raises_when_required_input_missing
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_load_from_input_entities_raises_when_required_input_missing
  fixtures: []
  markers: []
notes:
  behavior: Raises when a required input entity is missing.
  redundancy: Related to required field returns None test.
  decision_rationale: Keep. Required entity missing is an error.
---

# Behavior summary

Missing required input entity causes a ValueError.

# Redundancy / overlap

Pairs with required field returns None test.

# Decision rationale

Keep. Required entity missing is distinct from None value.

# Fixtures / setup

Mocks missing entity ID.

# Next actions

None.
