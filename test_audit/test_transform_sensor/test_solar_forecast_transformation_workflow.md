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
  nodeid: tests/test_transform_sensor.py::test_solar_forecast_transformation_workflow
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_solar_forecast_transformation_workflow
  fixtures: []
  markers: []
notes:
  behavior: End-to-end day_offset workflow shifts solar forecast timestamps to tomorrow.
  redundancy: Overlaps with main day_offset test; this one validates output correctness.
  decision_rationale: Keep. Stronger end-to-end verification; candidate to consolidate with main day_offset test.
---

# Behavior summary

Runs CLI day_offset on solar data and asserts output timestamps are shifted to tomorrow.

# Redundancy / overlap

Overlaps with `test_main_with_day_offset` but has stronger assertions.

# Decision rationale

Keep. Prefer this as the primary end-to-end day_offset test.

# Fixtures / setup

Uses `tmp_path`.

# Next actions

If trimming, fold `test_main_with_day_offset` into this test.
