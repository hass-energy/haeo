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
  nodeid: tests/test_coordinator.py::test_async_update_data_clears_flags_in_finally
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_update_data_clears_flags_in_finally
  fixtures: []
  markers: []
notes:
  behavior: Clears optimization flags even when update raises.
  redundancy: Unique finally-path coverage.
  decision_rationale: Keep. Prevents stuck flags.
---

# Behavior summary

Optimization flags are cleared in a finally block after errors.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures cleanup on failure.

# Fixtures / setup

Mocks update error path.

# Next actions

None.
