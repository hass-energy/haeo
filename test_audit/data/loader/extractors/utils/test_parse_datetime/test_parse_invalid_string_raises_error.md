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
  nodeid: tests/data/loader/extractors/utils/test_parse_datetime.py::test_parse_invalid_string_raises_error
  source_file: tests/data/loader/extractors/utils/test_parse_datetime.py
  test_class: ''
  test_function: test_parse_invalid_string_raises_error
  fixtures: []
  markers: []
notes:
  behavior: Invalid datetime strings raise ValueError.
  redundancy: Unique error path.
  decision_rationale: Keep. Ensures invalid input handling.
---

# Behavior summary

Invalid ISO strings raise ValueError.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Error handling is important.

# Fixtures / setup

None.

# Next actions

None.
