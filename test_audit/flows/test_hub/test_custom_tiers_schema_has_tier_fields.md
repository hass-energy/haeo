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
  nodeid: tests/flows/test_hub.py::test_custom_tiers_schema_has_tier_fields
  source_file: tests/flows/test_hub.py
  test_class: ''
  test_function: test_custom_tiers_schema_has_tier_fields
  fixtures: []
  markers: []
notes:
  behavior: Custom tiers schema includes all tier fields.
  redundancy: Schema coverage.
  decision_rationale: Keep. Ensures tier configuration fields exist.
---

# Behavior summary

Custom tiers schema includes all tier counts and durations.

# Redundancy / overlap

Complementary to simplified hub schema test.

# Decision rationale

Keep. Prevents schema regressions.

# Fixtures / setup

Uses custom tiers schema helper.

# Next actions

None.
