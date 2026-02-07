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
  nodeid: tests/elements/battery/test_adapter.py::test_model_elements_overcharge_only_adds_soc_pricing
  source_file: tests/elements/battery/test_adapter.py
  test_class: ''
  test_function: test_model_elements_overcharge_only_adds_soc_pricing
  fixtures: []
  markers: []
notes:
  behavior: SOC pricing segment includes charge threshold when overcharge is configured.
  redundancy: Unique SOC pricing behavior.
  decision_rationale: Keep. Overcharge pricing is important.
---

# Behavior summary

Overcharge-only configuration adds SOC pricing charge threshold.

# Redundancy / overlap

No overlap with other model element tests.

# Decision rationale

Keep. SOC pricing behavior should be validated.

# Fixtures / setup

Uses adapter model_elements.

# Next actions

None.
