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
  nodeid: tests/data/loader/test_time_series_loader.py::test_load_boundaries_raises_when_empty_entity_ids
  source_file: tests/data/loader/test_time_series_loader.py
  test_class: ''
  test_function: test_load_boundaries_raises_when_empty_entity_ids
  fixtures: []
  markers: []
notes:
  behavior: Raises when boundary load is called with empty entity list.
  redundancy: Boundary-specific validation path.
  decision_rationale: Keep. Required entities should be enforced.
---

# Behavior summary

Empty entity list raises for boundary load.

# Redundancy / overlap

Distinct from interval loader validation.

# Decision rationale

Keep. Boundary load should validate inputs.

# Fixtures / setup

None.

# Next actions

None.
