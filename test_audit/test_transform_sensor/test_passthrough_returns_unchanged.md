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
  nodeid: tests/test_transform_sensor.py::test_passthrough_returns_unchanged
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_passthrough_returns_unchanged
  fixtures: []
  markers: []
notes:
  behavior: Passthrough returns data unchanged by value.
  redundancy: Related to identity check but validates equality.
  decision_rationale: Keep. Confirms data content is preserved.
---

# Behavior summary

Verifies passthrough returns data equal to the input.

# Redundancy / overlap

Overlaps with identity test; can be combined if needed.

# Decision rationale

Keep. Equality check is useful even if identity test is combined.

# Fixtures / setup

Uses `sample_sigen_data`.

# Next actions

None.
