---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: Inverter with all outputs
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/elements/inverter/test_model.py::test_outputs_mapping
  source_file: tests/elements/inverter/test_model.py
  test_class: ''
  test_function: test_outputs_mapping
  fixtures: []
  markers: []
notes:
  behavior: Maps node and connection outputs into inverter device outputs, including active power and shadow prices.
  redundancy: Element output mapping tests are standard but element-specific.
  decision_rationale: Keep. Protects inverter output mapping.
---

# Behavior summary

Transforms model outputs into inverter sensor outputs.

# Redundancy / overlap

Pattern exists across elements but content is inverter-specific.

# Decision rationale

Keep. Ensures output mapping correctness.

# Fixtures / setup

Uses element registry and output data.

# Next actions

None.
