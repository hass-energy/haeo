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
  nodeid: tests/data/loader/extractors/utils/test_parse_datetime.py::test_parse_none_raises_error
  source_file: tests/data/loader/extractors/utils/test_parse_datetime.py
  test_class: ''
  test_function: test_parse_none_raises_error
  fixtures: []
  markers: []
notes:
  behavior: None input raises ValueError.
  redundancy: Unique error path.
  decision_rationale: Keep. None handling is important.
---

# Behavior summary

None input raises ValueError.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Error handling is important.

# Fixtures / setup

None.

# Next actions

None.
