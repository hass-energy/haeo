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
  nodeid: tests/test_coordinator.py::test_load_element_config_raises_for_unknown_element
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_load_element_config_raises_for_unknown_element
  fixtures: []
  markers: []
notes:
  behavior: Raises ValueError for unknown element names.
  redundancy: Distinct validation error.
  decision_rationale: Keep. Unknown elements should fail fast.
---

# Behavior summary

Unknown element names are rejected during config load.

# Redundancy / overlap

No overlap with invalid type validation.

# Decision rationale

Keep. Ensures invalid names are caught.

# Fixtures / setup

Mocks unknown element name.

# Next actions

None.
