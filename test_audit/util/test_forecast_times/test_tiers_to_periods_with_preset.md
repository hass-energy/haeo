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
  nodeid: tests/util/test_forecast_times.py::test_tiers_to_periods_with_preset
  source_file: tests/util/test_forecast_times.py
  test_class: ''
  test_function: test_tiers_to_periods_with_preset
  fixtures: []
  markers: []
notes:
  behavior: Smoke test for preset config producing periods and tier-1 starts.
  redundancy: Largely covered by preset invariant tests.
  decision_rationale: Combine or remove if pruning tests.
---

# Behavior summary

Ensures preset configuration yields periods and expected tier-1 start timing.

# Redundancy / overlap

Overlaps with preset invariant tests.

# Decision rationale

Combine. The invariant tests already cover preset behavior.

# Fixtures / setup

None.

# Next actions

Consider removing if keeping invariant tests.
