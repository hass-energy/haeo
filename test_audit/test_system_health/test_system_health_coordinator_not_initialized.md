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
  nodeid: tests/test_system_health.py::test_system_health_coordinator_not_initialized
  source_file: tests/test_system_health.py
  test_class: ''
  test_function: test_system_health_coordinator_not_initialized
  fixtures: []
  markers: []
notes:
  behavior: Marks entries without runtime data as coordinator_not_initialized.
  redundancy: Distinct from update_failed or ok status cases.
  decision_rationale: Keep. Validates explicit uninitialized state.
---

# Behavior summary

Patches entries with no runtime data and asserts system health reports coordinator_not_initialized.

# Redundancy / overlap

No overlap with initialized coordinator output cases.

# Decision rationale

Keep. Uninitialized state must be surfaced.

# Fixtures / setup

Uses `hass` and patching config entries.

# Next actions

None.
