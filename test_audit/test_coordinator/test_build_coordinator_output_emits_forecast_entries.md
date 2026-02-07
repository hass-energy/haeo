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
  nodeid: tests/test_coordinator.py::test_build_coordinator_output_emits_forecast_entries
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_build_coordinator_output_emits_forecast_entries
  fixtures: []
  markers: []
notes:
  behavior: Emits forecast entries when output values match forecast timestamps.
  redundancy: Core forecast mapping behavior.
  decision_rationale: Keep. Forecast payloads are critical.
---

# Behavior summary

Produces forecast payload when output values align with timestamps.

# Redundancy / overlap

No overlap with other output cases.

# Decision rationale

Keep. Ensures forecast mapping.

# Fixtures / setup

Uses forecast timestamps in output build.

# Next actions

None.
