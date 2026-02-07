---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: input_data0
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: not a config
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: None
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/elements/test_init.py::test_is_not_element_config_schema
  source_file: tests/elements/test_init.py
  test_class: ''
  test_function: test_is_not_element_config_schema
  fixtures: []
  markers: []
notes:
  behavior: Non-mapping inputs are rejected for schema validation.
  redundancy: Basic guard coverage.
  decision_rationale: Keep. Ensures type guard for schema inputs.
---

# Behavior summary

Non-mapping inputs return false for schema validation.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Base guard behavior.

# Fixtures / setup

None.

# Next actions

None.
