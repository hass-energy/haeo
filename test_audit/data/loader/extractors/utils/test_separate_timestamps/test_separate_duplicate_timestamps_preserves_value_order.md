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
  nodeid: tests/data/loader/extractors/utils/test_separate_timestamps.py::test_separate_duplicate_timestamps_preserves_value_order
  source_file: tests/data/loader/extractors/utils/test_separate_timestamps.py
  test_class: ''
  test_function: test_separate_duplicate_timestamps_preserves_value_order
  fixtures: []
  markers: []
notes:
  behavior: Preserves value ordering after separating duplicates.
  redundancy: Complements parameterized cases.
  decision_rationale: Keep. Order preservation is a key guarantee.
---

# Behavior summary

Value ordering is preserved even after duplicate separation.

# Redundancy / overlap

Some overlap with param cases but explicitly asserts order.

# Decision rationale

Keep. Order preservation is important.

# Fixtures / setup

None.

# Next actions

None.
