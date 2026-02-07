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
  nodeid: tests/elements/battery/test_adapter.py::test_available_returns_true_when_sensors_exist
  source_file: tests/elements/battery/test_adapter.py
  test_class: ''
  test_function: test_available_returns_true_when_sensors_exist
  fixtures: []
  markers: []
notes:
  behavior: Battery availability returns true when required sensors exist.
  redundancy: Base availability success case.
  decision_rationale: Keep. Confirms required-sensor availability.
---

# Behavior summary

Availability succeeds when required sensors are present.

# Redundancy / overlap

No overlap with missing-sensor cases.

# Decision rationale

Keep. Base availability behavior.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
