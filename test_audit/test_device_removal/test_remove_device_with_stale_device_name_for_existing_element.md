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
  nodeid: tests/test_device_removal.py::test_remove_device_with_stale_device_name_for_existing_element
  source_file: tests/test_device_removal.py
  test_class: ''
  test_function: test_remove_device_with_stale_device_name_for_existing_element
  fixtures: []
  markers: []
notes:
  behavior: Removes devices with stale name suffix even when subentry exists.
  redundancy: Unique stale-name scenario.
  decision_rationale: Keep. Ensures stale device cleanup.
---

# Behavior summary

Asserts devices with outdated name suffixes are removed despite existing subentries.

# Redundancy / overlap

No overlap with basic keep/remove cases.

# Decision rationale

Keep. Stale device cleanup is distinct.

# Fixtures / setup

Uses Home Assistant fixtures and mock config entries.

# Next actions

None.
