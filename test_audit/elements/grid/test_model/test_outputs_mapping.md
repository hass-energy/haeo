---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: Grid with import and export - cost/revenue calculated from power × price × period
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Grid with multiple periods - cumulative cost/revenue
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/elements/grid/test_model.py::test_outputs_mapping
  source_file: tests/elements/grid/test_model.py
  test_class: ''
  test_function: test_outputs_mapping
  fixtures: []
  markers: []
notes:
  behavior: Maps grid model outputs to device outputs with pricing and totals.
  redundancy: Core output mapping coverage.
  decision_rationale: Keep. Output mapping is critical.
---

# Behavior summary

Parameterized test validates grid output mapping and cost/revenue totals.

# Redundancy / overlap

No overlap with model element creation.

# Decision rationale

Keep. Output mapping is central.

# Fixtures / setup

Uses parameterized cases.

# Next actions

None.
