---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: 2_days
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: 3_days
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: 5_days
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: 7_days
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/util/test_forecast_times.py::test_preset_produces_constant_step_count_for_all_minutes
  source_file: tests/util/test_forecast_times.py
  test_class: ''
  test_function: test_preset_produces_constant_step_count_for_all_minutes
  fixtures: []
  markers: []
notes:
  behavior: Preset step count stays constant across all start minutes.
  redundancy: Complementary to exact horizon duration test.
  decision_rationale: Keep. Validates preset invariants.
---

# Behavior summary

Parameterized test ensures preset step counts remain constant across start minutes.

# Redundancy / overlap

No overlap with exact horizon duration test; covers a different invariant.

# Decision rationale

Keep. Preset invariants should be validated.

# Fixtures / setup

None.

# Next actions

None.
