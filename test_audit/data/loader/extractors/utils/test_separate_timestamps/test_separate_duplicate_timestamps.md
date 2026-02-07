---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: empty
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: single_entry
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: no_duplicates
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: one_duplicate_pair
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: multiple_duplicate_pairs
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: amber_step_function
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: mixed_pattern
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: three_consecutive_duplicates
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: four_consecutive_duplicates
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: five_consecutive_duplicates
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/data/loader/extractors/utils/test_separate_timestamps.py::test_separate_duplicate_timestamps
  source_file: tests/data/loader/extractors/utils/test_separate_timestamps.py
  test_class: ''
  test_function: test_separate_duplicate_timestamps
  fixtures: []
  markers: []
notes:
  behavior: Separates duplicate timestamps with step-function semantics across many cases.
  redundancy: Comprehensive parameter coverage.
  decision_rationale: Keep. Core helper behavior.
---

# Behavior summary

Parameterized test covers duplicate handling, step functions, and edge cases.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures correct duplicate timestamp handling.

# Fixtures / setup

None.

# Next actions

None.
