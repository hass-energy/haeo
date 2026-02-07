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
  nodeid: tests/test_transform_sensor.py::test_read_invalid_json
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_read_invalid_json
  fixtures: []
  markers: []
notes:
  behavior: Raises JSONDecodeError for invalid JSON content.
  redundancy: Unique error-path coverage.
  decision_rationale: Keep. Ensures parse errors are surfaced.
---

# Behavior summary

Writes invalid JSON and asserts JSONDecodeError is raised by `_read_json_file`.

# Redundancy / overlap

No overlap with missing-file error case.

# Decision rationale

Keep. Validates invalid JSON handling.

# Fixtures / setup

Uses `tmp_path`.

# Next actions

None.
