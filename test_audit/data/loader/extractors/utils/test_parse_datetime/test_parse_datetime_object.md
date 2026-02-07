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
  nodeid: tests/data/loader/extractors/utils/test_parse_datetime.py::test_parse_datetime_object
  source_file: tests/data/loader/extractors/utils/test_parse_datetime.py
  test_class: ''
  test_function: test_parse_datetime_object
  fixtures: []
  markers: []
notes:
  behavior: Parses datetime objects directly into timestamps.
  redundancy: Overlaps with no-timezone test.
  decision_rationale: Keep. Core datetime object handling.
---

# Behavior summary

Datetime objects are parsed into timestamps.

# Redundancy / overlap

Adjacent to no-timezone test.

# Decision rationale

Keep. Core datetime object parsing.

# Fixtures / setup

None.

# Next actions

None.
