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
  nodeid: tests/elements/battery/test_adapter.py::test_model_elements_omits_efficiency_when_missing
  source_file: tests/elements/battery/test_adapter.py
  test_class: ''
  test_function: test_model_elements_omits_efficiency_when_missing
  fixtures: []
  markers: []
notes:
  behavior: Efficiency segment defaults to None when not configured.
  redundancy: Distinct from efficiency-present test.
  decision_rationale: Keep. Default handling is important.
---

# Behavior summary

Model elements use default efficiency values when not provided.

# Redundancy / overlap

Pairs with efficiency-present test.

# Decision rationale

Keep. Default behavior should be validated.

# Fixtures / setup

Uses adapter model_elements.

# Next actions

None.
