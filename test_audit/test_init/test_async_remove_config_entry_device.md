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
  nodeid: tests/test_init.py::test_async_remove_config_entry_device
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_async_remove_config_entry_device
  fixtures: []
  markers: []
notes:
  behavior: Returns True for existing device removal and False when device is already removed.
  redundancy: Unique device registry behavior.
  decision_rationale: Keep. Validates device removal logic.
---

# Behavior summary

Creates a device, asserts removal returns True, then removes device and asserts a second removal returns False.

# Redundancy / overlap

No overlap with setup or update listener tests.

# Decision rationale

Keep. Device removal behavior is important.

# Fixtures / setup

Uses `mock_hub_entry` and device registry.

# Next actions

None.
