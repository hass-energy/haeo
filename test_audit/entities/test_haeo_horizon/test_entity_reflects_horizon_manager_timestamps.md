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
  nodeid: tests/entities/test_haeo_horizon.py::test_entity_reflects_horizon_manager_timestamps
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_entity_reflects_horizon_manager_timestamps
  fixtures: []
  markers: []
notes:
  behavior: Forecast timestamps mirror HorizonManager timestamps.
  redundancy: Core sync behavior.
  decision_rationale: Keep. Ensures timestamp alignment.
---

# Behavior summary

Entity forecast timestamps match horizon manager output.

# Redundancy / overlap

Complementary to forecast attribute structure tests.

# Decision rationale

Keep. Prevents timestamp mismatch.

# Fixtures / setup

Uses real HorizonManager.

# Next actions

None.
