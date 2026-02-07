---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: single_tier
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: multiple_tiers
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: all_tiers
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: empty_tiers
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/util/test_forecast_times.py::test_tiers_to_periods_seconds
  source_file: tests/util/test_forecast_times.py
  test_class: ''
  test_function: test_tiers_to_periods_seconds
  fixtures: []
  markers: []
notes:
  behavior: Expands tier counts/durations into per-period seconds for multiple tier patterns.
  redundancy: Base coverage for tier expansion behavior.
  decision_rationale: Keep. Core helper behavior.
---

# Behavior summary

Parameterized test validates tiers are expanded into correct per-period seconds across multiple patterns.

# Redundancy / overlap

Some overlap with preset/custom tests but this is the explicit-count baseline.

# Decision rationale

Keep. Ensures correct tier expansion.

# Fixtures / setup

None.

# Next actions

None.
