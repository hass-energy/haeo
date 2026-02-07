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
  nodeid: tests/data/loader/extractors/utils/test_parse_datetime.py::test_parse_datetime_string
  source_file: tests/data/loader/extractors/utils/test_parse_datetime.py
  test_class: ''
  test_function: test_parse_datetime_string
  fixtures: []
  markers: []
notes:
  behavior: Parses ISO datetime strings with timezone offsets.
  redundancy: Unique string parsing path.
  decision_rationale: Keep. Ensures string parsing correctness.
---

# Behavior summary

ISO datetime strings are parsed into UTC timestamps.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. String parsing is core.

# Fixtures / setup

None.

# Next actions

None.
