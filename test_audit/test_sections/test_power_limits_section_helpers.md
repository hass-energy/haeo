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
  nodeid: tests/test_sections.py::test_power_limits_section_helpers
  source_file: tests/test_sections.py
  test_class: ''
  test_function: test_power_limits_section_helpers
  fixtures: []
  markers: []
notes:
  behavior: Validates power limits section definition and field builder output.
  redundancy: Distinct section helper coverage.
  decision_rationale: Keep. Ensures power limits section helpers build expected schema entries.
---

# Behavior summary

Checks power limits section metadata and verifies field builder returns a selector marker for an included field.

# Redundancy / overlap

No overlap with other section helper tests; this is specific to power limits section.

# Decision rationale

Keep. Confirms power limits section helper behavior.

# Fixtures / setup

Uses `hass`.

# Next actions

None.
