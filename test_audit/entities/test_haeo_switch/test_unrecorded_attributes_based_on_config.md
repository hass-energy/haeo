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
      behavior: Default config excludes forecast attributes from recorder.
      redundancy: Covers default case.
    - id: True-False
      reviewed: true
      decision: keep
      behavior: Explicit record_forecasts includes forecast attributes.
      redundancy: Covers enabled case.
meta:
  nodeid: tests/entities/test_haeo_switch.py::test_unrecorded_attributes_based_on_config
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_unrecorded_attributes_based_on_config
  fixtures: []
  markers: []
notes:
  behavior: Recorder filtering respects record_forecasts config for switch forecasts.
  redundancy: Specific to recorder filtering.
  decision_rationale: Keep. Ensures recorder config behavior.
---

# Behavior summary

Forecast attributes are excluded by default and included when enabled.

# Redundancy / overlap

Unique recorder configuration behavior.

# Decision rationale

Keep. Prevents recorder configuration regressions.

# Fixtures / setup

Parameterized config entry with record_forecasts flag.

# Next actions

None.
