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
  nodeid: tests/entities/test_haeo_number.py::test_get_values_scales_percentage_fields
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_get_values_scales_percentage_fields
  fixtures: []
  markers: []
notes:
  behavior: Percentage fields are normalized to ratios in get_values.
  redundancy: Specific to percentage scaling.
  decision_rationale: Keep. Ensures unit conversion.
---

# Behavior summary

Converts percent to ratio values.

# Redundancy / overlap

Distinct from other get_values tests.

# Decision rationale

Keep. Prevents scaling regressions.

# Fixtures / setup

Uses percent field info.

# Next actions

None.
