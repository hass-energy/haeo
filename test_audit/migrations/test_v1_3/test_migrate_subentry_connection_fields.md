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
  nodeid: tests/migrations/test_v1_3.py::test_migrate_subentry_connection_fields
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_migrate_subentry_connection_fields
  fixtures: []
  markers: []
notes:
  behavior: Maps connection endpoints, power limits, pricing, and efficiency into sectioned data.
  redundancy: No other test asserts full connection mapping across all sections.
  decision_rationale: Keep to validate connection migration mapping.
---

# Behavior summary

Asserts endpoints and section values are converted into sectioned data with connection target/value wrappers.

# Redundancy / overlap

Unique coverage for connection migration across all sections.

# Decision rationale

Keep. Ensures connection migration remains correct.

# Fixtures / setup

None.

# Next actions

None.
