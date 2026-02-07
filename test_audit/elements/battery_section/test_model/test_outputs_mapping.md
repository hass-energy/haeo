---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: Battery section with all shadow prices
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Battery section without optional shadow prices
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/elements/battery_section/test_model.py::test_outputs_mapping
  source_file: tests/elements/battery_section/test_model.py
  test_class: ''
  test_function: test_outputs_mapping
  fixtures: []
  markers: []
notes:
  behavior: Maps battery section model outputs to device outputs with optional shadows.
  redundancy: Core output mapping coverage.
  decision_rationale: Keep. Output mapping is critical.
---

# Behavior summary

Parameterized test validates output mapping with and without shadow prices.

# Redundancy / overlap

No overlap with model element creation tests.

# Decision rationale

Keep. Output mapping is central.

# Fixtures / setup

Uses parameterized cases.

# Next actions

None.
