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
  nodeid: tests/test_coordinator.py::test_async_initialize_raises_without_runtime_data
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_initialize_raises_without_runtime_data
  fixtures: []
  markers: []
notes:
  behavior: Raises RuntimeError when initialization runs without runtime data.
  redundancy: Related to input-load missing runtime data guard.
  decision_rationale: Keep. Initialization should fail fast.
---

# Behavior summary

Initialization fails when runtime data is not available.

# Redundancy / overlap

Distinct from input-load guard path.

# Decision rationale

Keep. Prevents invalid initialization.

# Fixtures / setup

Mocks missing runtime data.

# Next actions

None.
