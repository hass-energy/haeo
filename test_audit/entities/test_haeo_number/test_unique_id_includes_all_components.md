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
  nodeid: tests/entities/test_haeo_number.py::test_unique_id_includes_all_components
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_unique_id_includes_all_components
  fixtures: []
  markers: []
notes:
  behavior: Unique ID combines entry ID, subentry ID, and field name.
  redundancy: Core entity identity behavior.
  decision_rationale: Keep. Ensures stable unique IDs.
---

# Behavior summary

Unique ID includes entry, subentry, and field key.

# Redundancy / overlap

Foundational identity behavior.

# Decision rationale

Keep. Prevents unique ID regressions.

# Fixtures / setup

Uses config entry and subentry.

# Next actions

None.
