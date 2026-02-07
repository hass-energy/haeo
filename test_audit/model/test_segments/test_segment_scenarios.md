---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: Passthrough forwards power unchanged
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Efficiency scales output power
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Power limit caps source-to-target flow
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Power limit caps target-to-source flow
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Fixed power limits enforce equality
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Time-slice constraint limits bidirectional flow
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Pricing adds cost to objective
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: SOC pricing applies costs outside thresholds
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: SOC pricing supports discharge-only penalty
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: SOC pricing supports charge-only penalty
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: SOC pricing passes through power
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/model/test_segments.py::test_segment_scenarios
  source_file: tests/model/test_segments.py
  test_class: ''
  test_function: test_segment_scenarios
  fixtures: []
  markers: []
notes:
  behavior: Segment scenarios validate expected behavior across segment types.
  redundancy: Distinct from error and output coverage tests.
  decision_rationale: Keep. Ensures segment behavior.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions
