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
  nodeid: tests/test_transform_sensor.py::test_read_nonexistent_file
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_read_nonexistent_file
  fixtures: []
  markers: []
notes:
  behavior: Raises FileNotFoundError for missing JSON file.
  redundancy: Unique error-path coverage.
  decision_rationale: Keep. Ensures error propagation.
---

# Behavior summary

Attempts to read a non-existent file and asserts FileNotFoundError is raised.

# Redundancy / overlap

No overlap with invalid JSON error.

# Decision rationale

Keep. Validates missing-file handling.

# Fixtures / setup

Uses `tmp_path`.

# Next actions

None.
