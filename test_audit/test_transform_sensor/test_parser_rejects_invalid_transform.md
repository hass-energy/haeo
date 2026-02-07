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
  nodeid: tests/test_transform_sensor.py::test_parser_rejects_invalid_transform
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_parser_rejects_invalid_transform
  fixtures: []
  markers: []
notes:
  behavior: Rejects invalid transform types at the CLI argument parser level.
  redundancy: Distinct from runtime unknown-transform validation.
  decision_rationale: Keep. Parser-level validation is important.
---

# Behavior summary

Asserts parser raises SystemExit when an invalid transform type is provided.

# Redundancy / overlap

No overlap with runtime unknown-transform error.

# Decision rationale

Keep. Validates CLI input validation.

# Fixtures / setup

None.

# Next actions

None.
