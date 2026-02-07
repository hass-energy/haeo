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
  nodeid: tests/util/test_forecast_times.py::test_tiers_to_periods_with_missing_tiers
  source_file: tests/util/test_forecast_times.py
  test_class: ''
  test_function: test_tiers_to_periods_with_missing_tiers
  fixtures: []
  markers: []
notes:
  behavior: Handles missing tier keys gracefully for custom presets.
  redundancy: Distinct missing-key behavior.
  decision_rationale: Keep. Missing tiers should be handled safely.
---

# Behavior summary

Ensures missing tier keys do not break period generation.

# Redundancy / overlap

No overlap with complete-tier cases.

# Decision rationale

Keep. Missing key handling is important.

# Fixtures / setup

None.

# Next actions

None.
