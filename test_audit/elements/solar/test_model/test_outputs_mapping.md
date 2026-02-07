---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: Solar with forecast limit
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Solar with shadow price output
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/elements/solar/test_model.py::test_outputs_mapping
  source_file: tests/elements/solar/test_model.py
  test_class: ''
  test_function: test_outputs_mapping
  fixtures: []
  markers: []
notes:
  behavior: Maps connection power and shadow price outputs into solar device outputs.
  redundancy: Element output mapping tests are standard but element-specific.
  decision_rationale: Keep. Ensures solar output mapping.
---

# Behavior summary

Transforms model outputs into solar sensor outputs.

# Redundancy / overlap

Pattern exists across elements but content is solar-specific.

# Decision rationale

Keep. Protects output mapping.

# Fixtures / setup

Uses element registry and output data.

# Next actions

None.
