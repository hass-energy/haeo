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
  nodeid: tests/test_coordinator.py::test_signal_optimization_stale_skips_when_auto_optimize_disabled
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_signal_optimization_stale_skips_when_auto_optimize_disabled
  fixtures: []
  markers: []
notes:
  behavior: No-op when auto optimize is disabled.
  redundancy: Distinct guard for auto optimize state.
  decision_rationale: Keep. Ensures disabled state blocks optimization.
---

# Behavior summary

Optimization signals are ignored when auto optimize is disabled.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Confirms auto optimize gate.

# Fixtures / setup

Mocks auto optimize disabled state.

# Next actions

None.
