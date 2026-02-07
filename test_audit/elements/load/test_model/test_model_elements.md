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
  nodeid: tests/elements/load/test_model.py::test_model_elements
  source_file: tests/elements/load/test_model.py
  test_class: ''
  test_function: test_model_elements
  fixtures: []
  markers: []
notes:
  behavior: Model elements mapping creates node and fixed power-limit connection from forecast.
  redundancy: Element model mapping tests are standard but element-specific.
  decision_rationale: Keep. Ensures load model composition is correct.
---

# Behavior summary

Builds node and fixed power-limit connection from forecast values.

# Redundancy / overlap

Pattern exists across elements but content is load-specific.

# Decision rationale

Keep. Protects load model mapping.

# Fixtures / setup

Uses element registry and normalize helper.

# Next actions

None.
