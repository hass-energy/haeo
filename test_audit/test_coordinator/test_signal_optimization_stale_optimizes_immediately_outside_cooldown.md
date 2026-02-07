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
  nodeid: tests/test_coordinator.py::test_signal_optimization_stale_optimizes_immediately_outside_cooldown
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_signal_optimization_stale_optimizes_immediately_outside_cooldown
  fixtures: []
  markers: []
notes:
  behavior: Triggers refresh immediately when cooldown has elapsed.
  redundancy: Complements cooldown scheduling tests.
  decision_rationale: Keep. Immediate refresh path is key.
---

# Behavior summary

Outside cooldown, optimization is triggered immediately.

# Redundancy / overlap

Complementary to cooldown scheduling test.

# Decision rationale

Keep. Ensures immediate refresh behavior.

# Fixtures / setup

Mocks cooldown timing.

# Next actions

None.
