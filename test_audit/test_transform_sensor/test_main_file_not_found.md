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
  nodeid: tests/test_transform_sensor.py::test_main_file_not_found
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_main_file_not_found
  fixtures: []
  markers: []
notes:
  behavior: Returns exit code 1 when input file is missing.
  redundancy: Unique CLI error path.
  decision_rationale: Keep. Validates file-not-found behavior.
---

# Behavior summary

Runs `main()` with a non-existent JSON file and asserts exit code 1.

# Redundancy / overlap

No overlap with invalid JSON or missing parameter errors.

# Decision rationale

Keep. Guards file-not-found handling.

# Fixtures / setup

Uses `tmp_path`.

# Next actions

None.
