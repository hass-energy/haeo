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
  nodeid: tests/test_transform_sensor.py::test_main_invalid_json
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_main_invalid_json
  fixtures: []
  markers: []
notes:
  behavior: Returns exit code 1 when input JSON is invalid.
  redundancy: Distinct CLI error path.
  decision_rationale: Keep. Validates parse error handling.
---

# Behavior summary

Runs `main()` with invalid JSON content and asserts exit code 1.

# Redundancy / overlap

No overlap with missing-file or missing-parameter cases.

# Decision rationale

Keep. CLI should fail on invalid JSON.

# Fixtures / setup

Uses `tmp_path`.

# Next actions

None.
