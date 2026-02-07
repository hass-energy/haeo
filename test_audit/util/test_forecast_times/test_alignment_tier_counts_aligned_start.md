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
  nodeid: tests/util/test_forecast_times.py::test_alignment_tier_counts_aligned_start
  source_file: tests/util/test_forecast_times.py
  test_class: ''
  test_function: test_alignment_tier_counts_aligned_start
  fixtures: []
  markers: []
notes:
  behavior: Validates tier count alignment when start is on the hour.
  redundancy: Complementary to mid-hour alignment test.
  decision_rationale: Keep. Alignment logic is important.
---

# Behavior summary

Ensures tier counts align correctly for hour-aligned starts.

# Redundancy / overlap

No overlap with mid-hour alignment scenario.

# Decision rationale

Keep. Alignment behavior is distinct.

# Fixtures / setup

None.

# Next actions

None.
