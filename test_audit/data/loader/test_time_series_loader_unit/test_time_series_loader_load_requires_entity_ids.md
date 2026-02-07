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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_time_series_loader_load_requires_entity_ids
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_time_series_loader_load_requires_entity_ids
  fixtures: []
  markers: []
notes:
  behavior: Raises when load is called without any entity IDs.
  redundancy: Unit-level input validation.
  decision_rationale: Keep. Required entities should be enforced.
---

# Behavior summary

Load rejects empty entity lists.

# Redundancy / overlap

Overlaps integration guard but at unit level.

# Decision rationale

Keep. Ensures input validation.

# Fixtures / setup

Uses Home Assistant fixture.

# Next actions

None.
