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
  nodeid: tests/test_services.py::test_save_diagnostics_schema_excludes_time_when_recorder_unavailable
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_save_diagnostics_schema_excludes_time_when_recorder_unavailable
  fixtures: []
  markers: []
notes:
  behavior: Service schema excludes `time` when recorder is unavailable.
  redundancy: Pairs with schema-includes test; can be parameterized.
  decision_rationale: Combine with schema-includes test.
---

# Behavior summary

Ensures save_diagnostics schema omits `time` when recorder integration is missing.

# Redundancy / overlap

Overlaps with schema-includes test.

# Decision rationale

Combine. Parameterize recorder availability.

# Fixtures / setup

Uses Home Assistant fixtures without recorder.

# Next actions

Consider merging with `test_save_diagnostics_schema_includes_time_when_recorder_available`.
