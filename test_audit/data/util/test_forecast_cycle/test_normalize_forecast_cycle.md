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
  nodeid: tests/data/util/test_forecast_cycle.py::test_normalize_forecast_cycle
  source_file: tests/data/util/test_forecast_cycle.py
  test_class: ''
  test_function: test_normalize_forecast_cycle
  fixtures: []
  markers: []
notes:
  behavior: Normalizes forecast cycles to align with the requested horizon start.
  redundancy: Distinct from fusion and combination utilities.
  decision_rationale: Keep. Cycling ensures complete horizon coverage.
---

# Behavior summary

Validates forecast cycling behavior for different offsets and horizon lengths.

# Redundancy / overlap

No overlap with fuser or combiner tests.

# Decision rationale

Keep. Cycling is core to forecast preparation.

# Fixtures / setup

None.

# Next actions

None.
