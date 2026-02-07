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
  nodeid: tests/test_coordinator.py::test_build_coordinator_output_uses_last_value_when_state_last
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_build_coordinator_output_uses_last_value_when_state_last
  fixtures: []
  markers: []
notes:
  behavior: Uses last value as state when state_last is enabled.
  redundancy: Distinct from other forecast/state selection logic.
  decision_rationale: Keep. State selection flag should be honored.
---

# Behavior summary

When state_last is set, the last value becomes the sensor state.

# Redundancy / overlap

No overlap with other output selection rules.

# Decision rationale

Keep. Validates state selection behavior.

# Fixtures / setup

Uses output payload with state_last.

# Next actions

None.
