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
  nodeid: tests/entities/test_haeo_horizon.py::test_horizon_manager_scheduled_update_reschedules
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_horizon_manager_scheduled_update_reschedules
  fixtures: []
  markers: []
notes:
  behavior: Scheduled update reschedules next timer.
  redundancy: Core manager scheduling behavior.
  decision_rationale: Keep. Ensures update timer is re-armed.
---

# Behavior summary

Scheduled update sets a new timer.

# Redundancy / overlap

Complementary to pause/resume timer tests.

# Decision rationale

Keep. Prevents scheduling regressions.

# Fixtures / setup

Clears timer before scheduled update.

# Next actions

None.
