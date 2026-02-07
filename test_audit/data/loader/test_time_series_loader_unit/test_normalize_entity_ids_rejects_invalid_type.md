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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_normalize_entity_ids_rejects_invalid_type
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_normalize_entity_ids_rejects_invalid_type
  fixtures: []
  markers: []
notes:
  behavior: Rejects non-string/non-sequence inputs for entity ID normalization.
  redundancy: Overlaps with sensor loader normalization test but at unit level.
  decision_rationale: Keep. Unit-level guard behavior.
---

# Behavior summary

Normalization rejects invalid types.

# Redundancy / overlap

Overlaps with sensor loader normalization test but at unit boundary.

# Decision rationale

Keep. Unit-level guard coverage.

# Fixtures / setup

None.

# Next actions

None.
