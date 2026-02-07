---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: Load with forecast
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/elements/load/test_model.py::test_outputs_mapping
  source_file: tests/elements/load/test_model.py
  test_class: ''
  test_function: test_outputs_mapping
  fixtures: []
  markers: []
notes:
  behavior: Maps connection power and shadow price outputs into load device outputs.
  redundancy: Element output mapping tests are standard but element-specific.
  decision_rationale: Keep. Protects load output mapping.
---

# Behavior summary

Transforms model outputs into load sensor outputs.

# Redundancy / overlap

Pattern exists across elements but content is load-specific.

# Decision rationale

Keep. Ensures output mapping correctness.

# Fixtures / setup

Uses element registry and output data.

# Next actions

None.
