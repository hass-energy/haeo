---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: None
      reviewed: true
      decision: keep
      behavior: Skips migration when element_type is missing.
      redundancy: Pairs with network case to cover non-element skip conditions.
    - id: network
      reviewed: true
      decision: keep
      behavior: Skips migration when element_type is network.
      redundancy: Distinct from missing element_type; covers network entry exclusion.
meta:
  nodeid: tests/migrations/test_v1_3.py::test_migrate_subentry_returns_none_for_non_elements
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_migrate_subentry_returns_none_for_non_elements
  fixtures: []
  markers: []
notes:
  behavior: Verifies subentry migration returns None for missing or network element types.
  redundancy: No other tests explicitly cover these skip conditions.
  decision_rationale: Ensures migration ignores non-element or network subentries.
---

# Behavior summary

Parameterized test that asserts \_migrate_subentry_data returns None when element_type is absent or network.

# Redundancy / overlap

Unique skip-path coverage for non-element subentries.

# Decision rationale

Keep. Guards migration filtering logic.

# Fixtures / setup

None.

# Next actions

None.
