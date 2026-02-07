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
  nodeid: tests/test_coordinator.py::test_load_element_config_raises_on_required_none_value
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_load_element_config_raises_on_required_none_value
  fixtures: []
  markers: []
notes:
  behavior: Raises when a required input field resolves to None.
  redundancy: Related to load-from-inputs None handling but targets narrower helper.
  decision_rationale: Keep. Validates required field enforcement.
---

# Behavior summary

Required fields cannot resolve to None during element config load.

# Redundancy / overlap

Overlaps with load-from-inputs None handling but different function.

# Decision rationale

Keep. Ensures required field validation.

# Fixtures / setup

Uses element config load helper.

# Next actions

None.
