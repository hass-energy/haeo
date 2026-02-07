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
  nodeid: tests/test_coordinator.py::test_load_from_input_entities_raises_for_invalid_config_data
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_load_from_input_entities_raises_for_invalid_config_data
  fixtures: []
  markers: []
notes:
  behavior: Raises when config data fails schema validation after input load.
  redundancy: Distinct from invalid element type validation.
  decision_rationale: Keep. Ensures schema validation enforcement.
---

# Behavior summary

Schema validation failure raises during input loading.

# Redundancy / overlap

No overlap with invalid element type test.

# Decision rationale

Keep. Config validation must fail fast.

# Fixtures / setup

Mocks invalid config payload.

# Next actions

None.
