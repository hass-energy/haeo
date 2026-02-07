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
  nodeid: tests/data/loader/test_constant_loader.py::test_constant_loader_invalid_type
  source_file: tests/data/loader/test_constant_loader.py
  test_class: ''
  test_function: test_constant_loader_invalid_type
  fixtures: []
  markers: []
notes:
  behavior: Raises on invalid types and succeeds on valid int load.
  redundancy: Overlaps with wrong-type tests but also covers success path in same test.
  decision_rationale: Keep. Provides combined error/success coverage.
---

# Behavior summary

Invalid types raise, valid types load successfully.

# Redundancy / overlap

Some overlap with wrong-type tests; this also asserts success path.

# Decision rationale

Keep. Combined error/success behavior is useful.

# Fixtures / setup

None.

# Next actions

None.
