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
  nodeid: tests/elements/test_init.py::test_config_schemas_match_element_types
  source_file: tests/elements/test_init.py
  test_class: ''
  test_function: test_config_schemas_match_element_types
  fixtures: []
  markers: []
notes:
  behavior: Ensures every element type has a config schema registered.
  redundancy: Unique registry invariant.
  decision_rationale: Keep. Ensures registry completeness.
---

# Behavior summary

All element types are present in ELEMENT_CONFIG_SCHEMAS.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Registry completeness is important.

# Fixtures / setup

None.

# Next actions

None.
