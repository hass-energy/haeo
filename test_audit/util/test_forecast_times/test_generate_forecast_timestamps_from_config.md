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
  nodeid: tests/util/test_forecast_times.py::test_generate_forecast_timestamps_from_config
  source_file: tests/util/test_forecast_times.py
  test_class: ''
  test_function: test_generate_forecast_timestamps_from_config
  fixtures: []
  markers: []
notes:
  behavior: Generates timestamps from config-based tiers using a rounded current time.
  redundancy: Related to default-start test; separate API entry point.
  decision_rationale: Keep. Config-based generation should be validated.
---

# Behavior summary

Ensures config-based timestamp generation uses rounded time and correct boundaries.

# Redundancy / overlap

Some overlap with default-start test but distinct API path.

# Decision rationale

Keep. Config-based behavior is important.

# Fixtures / setup

Uses time mocking.

# Next actions

None.
