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
  nodeid: tests/entities/test_haeo_number.py::test_async_load_data_with_empty_values_list
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_async_load_data_with_empty_values_list
  fixtures: []
  markers: []
notes:
  behavior: Empty interval load returns early without state changes.
  redundancy: Overlaps with empty-values test; keep this one.
  decision_rationale: Keep. Exercises load_intervals path.
---

# Behavior summary

No state update when interval loader returns empty list.

# Redundancy / overlap

Similar to empty-values test using generic loader.

# Decision rationale

Keep. Covers async interval loader path.

# Fixtures / setup

Mocks load_intervals AsyncMock.

# Next actions

None.
