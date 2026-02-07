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
  nodeid: tests/test_sections.py::test_efficiency_section_helpers
  source_file: tests/test_sections.py
  test_class: ''
  test_function: test_efficiency_section_helpers
  fixtures: []
  markers: []
notes:
  behavior: Validates efficiency section definition and field builder output.
  redundancy: Distinct section helper coverage.
  decision_rationale: Keep. Ensures section helpers build expected schema entries.
---

# Behavior summary

Checks efficiency section metadata and verifies field builder returns a selector marker for an included field.

# Redundancy / overlap

No overlap with other section helper tests; this is specific to efficiency section.

# Decision rationale

Keep. Confirms efficiency section helper behavior.

# Fixtures / setup

Uses `hass`.

# Next actions

None.
