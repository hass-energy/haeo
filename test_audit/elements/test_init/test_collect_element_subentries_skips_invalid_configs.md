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
  nodeid: tests/elements/test_init.py::test_collect_element_subentries_skips_invalid_configs
  source_file: tests/elements/test_init.py
  test_class: ''
  test_function: test_collect_element_subentries_skips_invalid_configs
  fixtures: []
  markers: []
notes:
  behavior: Skips invalid element subentries when collecting.
  redundancy: Unique integration behavior.
  decision_rationale: Keep. Ensures invalid configs are skipped.
---

# Behavior summary

Invalid element subentries are skipped during collection.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Protects against invalid subentries.

# Fixtures / setup

Uses MockConfigEntry and ConfigSubentry.

# Next actions

None.
