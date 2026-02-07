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
  nodeid: tests/elements/test_availability.py::test_schema_config_available_handles_nested_entity
  source_file: tests/elements/test_availability.py
  test_class: ''
  test_function: test_schema_config_available_handles_nested_entity
  fixtures: []
  markers: []
notes:
  behavior: Traverses nested config values and checks availability for nested entity values.
  redundancy: Unique nested traversal behavior.
  decision_rationale: Keep. Ensures nested configs are handled.
---

# Behavior summary

Nested entity values are checked for availability.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Nested config traversal is core.

# Fixtures / setup

Uses monkeypatched TimeSeriesLoader.available.

# Next actions

None.
