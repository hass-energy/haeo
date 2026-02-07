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
  nodeid: tests/test_coordinator.py::test_load_from_input_entities_loads_time_series_fields
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_load_from_input_entities_loads_time_series_fields
  fixtures: []
  markers: []
notes:
  behavior: Loads time-series inputs into numpy arrays for model usage.
  redundancy: Unique to time-series input path.
  decision_rationale: Keep. Validates time-series loading.
---

# Behavior summary

Time-series input fields are loaded and converted into arrays.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures time-series fields load correctly.

# Fixtures / setup

Uses time-series input field data.

# Next actions

None.
