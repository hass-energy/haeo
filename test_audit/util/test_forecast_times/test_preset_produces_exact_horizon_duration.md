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
  nodeid: tests/util/test_forecast_times.py::test_preset_produces_exact_horizon_duration
  source_file: tests/util/test_forecast_times.py
  test_class: ''
  test_function: test_preset_produces_exact_horizon_duration
  fixtures: []
  markers: []
notes:
  behavior: Preset total duration matches expected horizon minutes across start minutes.
  redundancy: Complementary to constant step count test.
  decision_rationale: Keep. Validates horizon duration invariant.
---

# Behavior summary

Parameterized test verifies total horizon duration matches preset minutes for all start times.

# Redundancy / overlap

No overlap with step-count invariant; this is duration-specific.

# Decision rationale

Keep. Preset duration invariants are important.

# Fixtures / setup

None.

# Next actions

None.
