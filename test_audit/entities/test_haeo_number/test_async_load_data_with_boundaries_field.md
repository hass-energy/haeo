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
  nodeid: tests/entities/test_haeo_number.py::test_async_load_data_with_boundaries_field
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_async_load_data_with_boundaries_field
  fixtures: []
  markers: []
notes:
  behavior: Boundaries fields use load_boundaries and return n+1 scaled values.
  redundancy: Specific to boundaries data loading.
  decision_rationale: Keep. Ensures boundaries loader path.
---

# Behavior summary

Uses boundary loader and scales percent to ratios.

# Redundancy / overlap

Distinct from interval load tests.

# Decision rationale

Keep. Protects boundary load path.

# Fixtures / setup

Mocks load_boundaries and load_intervals.

# Next actions

None.
