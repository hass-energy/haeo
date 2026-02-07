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
  nodeid: tests/test_services.py::test_save_diagnostics_schema_includes_time_when_recorder_available
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_save_diagnostics_schema_includes_time_when_recorder_available
  fixtures: []
  markers: []
notes:
  behavior: Service schema includes `time` when recorder is available.
  redundancy: Pairs with schema-excludes test; can be parameterized.
  decision_rationale: Combine with schema-excludes test.
---

# Behavior summary

Ensures save_diagnostics schema allows `time` when recorder is present.

# Redundancy / overlap

Overlaps with schema-excludes test.

# Decision rationale

Combine. Parameterize recorder availability.

# Fixtures / setup

Uses Home Assistant fixtures with recorder present.

# Next actions

Consider merging with `test_save_diagnostics_schema_excludes_time_when_recorder_unavailable`.
