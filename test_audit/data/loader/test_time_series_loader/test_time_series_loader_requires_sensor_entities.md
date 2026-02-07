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
  nodeid: tests/data/loader/test_time_series_loader.py::test_time_series_loader_requires_sensor_entities
  source_file: tests/data/loader/test_time_series_loader.py
  test_class: ''
  test_function: test_time_series_loader_requires_sensor_entities
  fixtures: []
  markers: []
notes:
  behavior: Empty entity list makes loader unavailable and load raises.
  redundancy: Integration-level guard for empty entity list.
  decision_rationale: Keep. Enforces required entities.
---

# Behavior summary

Empty entity lists are rejected for availability and load.

# Redundancy / overlap

Overlaps unit test but covers HA integration.

# Decision rationale

Keep. Ensures guard at integration level.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
