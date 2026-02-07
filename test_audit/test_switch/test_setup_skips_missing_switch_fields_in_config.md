---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_switch.py::test_setup_skips_missing_switch_fields_in_config
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_setup_skips_missing_switch_fields_in_config
  fixtures: []
  markers: []
notes:
  behavior: Skips optional switch creation when config field is missing.
  redundancy: Overlaps with curtailment creation; can be a parameterized variant.
  decision_rationale: Combine with curtailment creation test if consolidating.
---

# Behavior summary

Ensures missing optional switch fields do not create a switch entity.

# Redundancy / overlap

Overlaps with curtailment switch creation test.

# Decision rationale

Combine. Parameterize the presence/absence of the field.

# Fixtures / setup

Uses Home Assistant fixtures and mock solar subentry.

# Next actions

Consider merging with `test_setup_creates_switch_entities_for_solar_curtailment`.
