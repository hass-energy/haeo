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
  nodeid: tests/elements/test_availability.py::test_schema_config_available_returns_false_for_unavailable_entity
  source_file: tests/elements/test_availability.py
  test_class: ''
  test_function: test_schema_config_available_returns_false_for_unavailable_entity
  fixtures: []
  markers: []
notes:
  behavior: Returns false when an entity value is unavailable.
  redundancy: Unique availability helper path.
  decision_rationale: Keep. Ensures unavailable entities block availability.
---

# Behavior summary

Unavailable entity values cause availability to return false.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Availability must respect missing entities.

# Fixtures / setup

Uses monkeypatch on TimeSeriesLoader.available.

# Next actions

None.
