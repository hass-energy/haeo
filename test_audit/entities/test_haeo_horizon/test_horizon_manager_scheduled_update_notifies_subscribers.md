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
  nodeid: tests/entities/test_haeo_horizon.py::test_horizon_manager_scheduled_update_notifies_subscribers
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_horizon_manager_scheduled_update_notifies_subscribers
  fixtures: []
  markers: []
notes:
  behavior: Scheduled update notifies subscribers.
  redundancy: Core manager notification behavior.
  decision_rationale: Keep. Ensures subscribers are notified.
---

# Behavior summary

Scheduled update triggers subscriber callbacks.

# Redundancy / overlap

Complementary to resume/pause tests.

# Decision rationale

Keep. Prevents notification regressions.

# Fixtures / setup

Uses manual scheduled update call.

# Next actions

None.
