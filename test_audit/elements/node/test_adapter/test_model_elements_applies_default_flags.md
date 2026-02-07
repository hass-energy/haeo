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
  nodeid: tests/elements/node/test_adapter.py::test_model_elements_applies_default_flags
  source_file: tests/elements/node/test_adapter.py
  test_class: ''
  test_function: test_model_elements_applies_default_flags
  fixtures: []
  markers: []
notes:
  behavior: Model elements apply default role flags when missing.
  redundancy: Node-specific default behavior.
  decision_rationale: Keep. Protects default role handling.
---

# Behavior summary

Missing role flags default to `is_source=False`, `is_sink=False`.

# Redundancy / overlap

Unique to node role defaults.

# Decision rationale

Keep. Ensures defaults are applied.

# Fixtures / setup

Uses adapter directly.

# Next actions

None.
