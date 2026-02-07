---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/data/loader/extractors/utils/test_parse_datetime.py::test_parse_datetime_object_no_timezone
  source_file: tests/data/loader/extractors/utils/test_parse_datetime.py
  test_class: ''
  test_function: test_parse_datetime_object_no_timezone
  fixtures: []
  markers: []
notes:
  behavior: Intended to cover naive datetime handling, but uses tz-aware input.
  redundancy: Overlaps with datetime object test.
  decision_rationale: Combine or fix to use naive datetime.
---

# Behavior summary

Duplicates datetime object parsing coverage; input is not actually naive.

# Redundancy / overlap

Overlaps with datetime object parsing test.

# Decision rationale

Combine or adjust to use a truly naive datetime.

# Fixtures / setup

None.

# Next actions

Consider changing input to naive datetime.
