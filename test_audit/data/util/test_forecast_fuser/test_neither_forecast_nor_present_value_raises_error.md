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
  nodeid: tests/data/util/test_forecast_fuser.py::test_neither_forecast_nor_present_value_raises_error
  source_file: tests/data/util/test_forecast_fuser.py
  test_class: ''
  test_function: test_neither_forecast_nor_present_value_raises_error
  fixtures: []
  markers: []
notes:
  behavior: Raises ValueError when both forecast and present value are missing.
  redundancy: Distinct error path for interval fusion.
  decision_rationale: Keep. Enforces required inputs.
---

# Behavior summary

Missing forecast and present value raises a ValueError.

# Redundancy / overlap

Separate from boundary fusion error test.

# Decision rationale

Keep. Ensures correct error handling.

# Fixtures / setup

None.

# Next actions

None.
