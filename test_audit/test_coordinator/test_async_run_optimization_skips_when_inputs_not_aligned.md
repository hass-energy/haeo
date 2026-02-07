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
  nodeid: tests/test_coordinator.py::test_async_run_optimization_skips_when_inputs_not_aligned
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_run_optimization_skips_when_inputs_not_aligned
  fixtures: []
  markers: []
notes:
  behavior: Skips refresh when inputs are misaligned.
  redundancy: Pairs with aligned test.
  decision_rationale: Keep. Confirms misalignment guard.
---

# Behavior summary

Optimization does not run when inputs are misaligned.

# Redundancy / overlap

Paired with aligned optimization test.

# Decision rationale

Keep. Ensures alignment guard.

# Fixtures / setup

Mocks misaligned input state.

# Next actions

None.
