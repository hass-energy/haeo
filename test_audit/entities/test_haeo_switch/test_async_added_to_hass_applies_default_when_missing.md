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
  nodeid: tests/entities/test_haeo_switch.py::test_async_added_to_hass_applies_default_when_missing
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_async_added_to_hass_applies_default_when_missing
  fixtures: []
  markers: []
notes:
  behavior: Editable mode applies defaults when config value missing.
  redundancy: Specific to default handling.
  decision_rationale: Keep. Ensures defaults apply on add.
---

# Behavior summary

Defaults are applied when config field is missing.

# Redundancy / overlap

Complementary to None and defaults tests.

# Decision rationale

Keep. Validates defaults behavior.

# Fixtures / setup

Uses field info defaults.

# Next actions

None.
