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
  nodeid: tests/test_transform_sensor.py::test_transform_preserves_z_suffix
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_transform_preserves_z_suffix
  fixtures: []
  markers: []
notes:
  behavior: Ensures transformed timestamps preserve the Z suffix.
  redundancy: Specific suffix handling; complements all-fields test.
  decision_rationale: Keep. Z suffix is a common input format.
---

# Behavior summary

Transforms a Z-suffixed timestamp and verifies the suffix remains after shifting.

# Redundancy / overlap

Partial overlap with all-fields test but focuses on suffix preservation.

# Decision rationale

Keep. Prevents regressions in Z suffix handling.

# Fixtures / setup

None.

# Next actions

None.
