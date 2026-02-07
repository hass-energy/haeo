---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/elements/load/test_adapter.py::test_inputs_returns_input_fields
  source_file: tests/elements/load/test_adapter.py
  test_class: ''
  test_function: test_inputs_returns_input_fields
  fixtures: []
  markers: []
notes:
  behavior: inputs() exposes forecast fields for load.
  redundancy: Pattern exists across element adapters but fields are element-specific.
  decision_rationale: Keep. Ensures forecast inputs are declared.
---

# Behavior summary

Forecast section includes the `forecast` input field.

# Redundancy / overlap

Similar to other element input tests but field names differ.

# Decision rationale

Keep. Confirms input exposure.

# Fixtures / setup

Uses config schema data.

# Next actions

None.
