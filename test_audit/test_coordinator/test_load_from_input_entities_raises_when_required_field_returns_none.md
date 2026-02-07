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
  nodeid: tests/test_coordinator.py::test_load_from_input_entities_raises_when_required_field_returns_none
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_load_from_input_entities_raises_when_required_field_returns_none
  fixtures: []
  markers: []
notes:
  behavior: Raises when required field returns None values.
  redundancy: Related to required input missing test.
  decision_rationale: Keep. Required None should fail.
---

# Behavior summary

Required fields returning None values cause a ValueError.

# Redundancy / overlap

Pairs with required input missing test.

# Decision rationale

Keep. Distinct from missing entity case.

# Fixtures / setup

Mocks input field returning None.

# Next actions

None.
