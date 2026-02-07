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
  nodeid: tests/data/loader/extractors/utils/test_parse_datetime.py::test_parse_non_datetime_type_raises_error
  source_file: tests/data/loader/extractors/utils/test_parse_datetime.py
  test_class: ''
  test_function: test_parse_non_datetime_type_raises_error
  fixtures: []
  markers: []
notes:
  behavior: Non-datetime/non-string types raise ValueError.
  redundancy: Unique error path.
  decision_rationale: Keep. Input validation is important.
---

# Behavior summary

Invalid input types raise ValueError.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures robust input validation.

# Fixtures / setup

None.

# Next actions

None.
