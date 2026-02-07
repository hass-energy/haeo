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
  nodeid: tests/util/test_forecast_times.py::test_tiers_to_periods_with_custom
  source_file: tests/util/test_forecast_times.py
  test_class: ''
  test_function: test_tiers_to_periods_with_custom
  fixtures: []
  markers: []
notes:
  behavior: Validates explicit custom tier counts/durations.
  redundancy: Complementary to base tier expansion tests.
  decision_rationale: Keep. Covers custom preset branch.
---

# Behavior summary

Ensures custom tier counts/durations are expanded correctly.

# Redundancy / overlap

Some overlap with basic tier expansion but distinct config path.

# Decision rationale

Keep. Custom configuration is important.

# Fixtures / setup

None.

# Next actions

None.
