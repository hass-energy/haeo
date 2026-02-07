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
  nodeid: tests/test_services.py::test_save_diagnostics_with_historical_time
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_save_diagnostics_with_historical_time
  fixtures: []
  markers: []
notes:
  behavior: Uses HistoricalStateProvider for diagnostics at a specific time and includes that time in filename.
  redundancy: Distinct behavior from current-time diagnostics.
  decision_rationale: Keep. Validates historical diagnostics support.
---

# Behavior summary

Asserts historical diagnostics are collected using the requested time and filename reflects the historical timestamp.

# Redundancy / overlap

No overlap with standard diagnostics tests.

# Decision rationale

Keep. Historical diagnostics is distinct functionality.

# Fixtures / setup

Uses Home Assistant fixtures and temp directory.

# Next actions

None.
