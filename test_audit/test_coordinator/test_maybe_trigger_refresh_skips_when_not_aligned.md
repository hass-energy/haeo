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
  nodeid: tests/test_coordinator.py::test_maybe_trigger_refresh_skips_when_not_aligned
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_maybe_trigger_refresh_skips_when_not_aligned
  fixtures: []
  markers: []
notes:
  behavior: Skips refresh when input horizons are misaligned.
  redundancy: Pairs with aligned refresh test.
  decision_rationale: Keep. Misalignment handling is important.
---

# Behavior summary

Misaligned inputs prevent refresh from running.

# Redundancy / overlap

Paired with aligned refresh test.

# Decision rationale

Keep. Ensures alignment guard is enforced.

# Fixtures / setup

Uses alignment helper.

# Next actions

None.
