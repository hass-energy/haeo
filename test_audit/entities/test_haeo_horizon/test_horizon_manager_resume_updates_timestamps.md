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
  nodeid: tests/entities/test_haeo_horizon.py::test_horizon_manager_resume_updates_timestamps
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_horizon_manager_resume_updates_timestamps
  fixtures: []
  markers: []
notes:
  behavior: Resume refreshes timestamps.
  redundancy: Core resume behavior.
  decision_rationale: Keep. Ensures timestamps update after pause.
---

# Behavior summary

Resume updates forecast timestamps and keeps expected length.

# Redundancy / overlap

Complementary to resume notifications/timer tests.

# Decision rationale

Keep. Prevents stale timestamps.

# Fixtures / setup

Pauses and resumes manager.

# Next actions

None.
