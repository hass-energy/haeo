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
  nodeid: tests/test_coordinator.py::test_load_from_input_entities_raises_for_invalid_element_type
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_load_from_input_entities_raises_for_invalid_element_type
  fixtures: []
  markers: []
notes:
  behavior: Raises when element type is invalid in participant configs.
  redundancy: Distinct validation error path.
  decision_rationale: Keep. Invalid element types should fail early.
---

# Behavior summary

Invalid element types cause input loading to fail.

# Redundancy / overlap

No overlap with invalid config data test.

# Decision rationale

Keep. Ensures element type validation.

# Fixtures / setup

Mocks invalid element type.

# Next actions

None.
