---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/entities/test_haeo_number.py::test_async_load_data_handles_empty_values
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_async_load_data_handles_empty_values
  fixtures: []
  markers: []
notes:
  behavior: Empty loader values keep state unchanged.
  redundancy: Overlaps with empty values list test using load_intervals.
  decision_rationale: Combine into a single empty-values test.
---

# Behavior summary

Empty load results do not update entity state.

# Redundancy / overlap

Duplicated by empty-values list test.

# Decision rationale

Combine. Prefer single empty-values test.

# Fixtures / setup

Mocks loader to return empty list.

# Next actions

Consider merging with empty-values list test.
