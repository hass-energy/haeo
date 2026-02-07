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
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::test_invalid_sensor_handling
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: ''
  test_function: test_invalid_sensor_handling
  fixtures:
    - hass
  markers: []
notes:
  behavior: Invalid forecast formats fall back to simple value extraction.
  redundancy: Unique invalid-format coverage across multiple parsers.
  decision_rationale: Keep. Ensures robust fallback behavior.
---

# Behavior summary

Invalid forecast payloads fall back to numeric state extraction.

# Redundancy / overlap

No overlap; this is the primary invalid-format coverage.

# Decision rationale

Keep. Ensures fallback behavior across formats.

# Fixtures / setup

Uses ALL_INVALID_SENSORS fixtures.

# Next actions

None.
