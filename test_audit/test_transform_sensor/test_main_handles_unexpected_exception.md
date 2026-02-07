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
  nodeid: tests/test_transform_sensor.py::test_main_handles_unexpected_exception
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_main_handles_unexpected_exception
  fixtures: []
  markers: []
notes:
  behavior: Returns exit code 1 when unexpected exceptions occur during transform.
  redundancy: Unique defensive path coverage.
  decision_rationale: Keep. Ensures robust CLI failure handling.
---

# Behavior summary

Mocks `_apply_transform` to raise and asserts `main()` returns exit code 1.

# Redundancy / overlap

No overlap with other failure cases.

# Decision rationale

Keep. Guards unexpected exception handling.

# Fixtures / setup

Uses `tmp_path` and mocking for `_apply_transform`.

# Next actions

None.
