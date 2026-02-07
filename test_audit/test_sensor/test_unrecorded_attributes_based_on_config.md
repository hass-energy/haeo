---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: False-True
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: True-False
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/test_sensor.py::test_unrecorded_attributes_based_on_config
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_unrecorded_attributes_based_on_config
  fixtures: []
  markers: []
notes:
  behavior: Sets unrecorded attributes based on recorder configuration.
  redundancy: Unique recorder configuration behavior.
  decision_rationale: Keep. Ensures recorder attributes are filtered correctly.
---

# Behavior summary

Parameterized test that validates unrecorded attributes are set based on recorder settings.

# Redundancy / overlap

No overlap with other sensor tests.

# Decision rationale

Keep. Recorder behavior should be validated.

# Fixtures / setup

Uses Home Assistant fixtures and parametrization.

# Next actions

None.
