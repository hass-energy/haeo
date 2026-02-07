---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: price_pattern0
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: price_pattern1
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: price_pattern2
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/schema/test_util.py::test_price_patterns_match_common_currencies
  source_file: tests/schema/test_util.py
  test_class: ''
  test_function: test_price_patterns_match_common_currencies
  fixtures: []
  markers: []
notes:
  behavior: Validates that common currency price patterns are recognized.
  redundancy: Complements unit spec matching coverage.
  decision_rationale: Keep. Ensures currency pattern support stays stable.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions
