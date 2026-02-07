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
  nodeid: tests/data/loader/extractors/utils/test_base_unit.py::test_convert_to_base_unit
  source_file: tests/data/loader/extractors/utils/test_base_unit.py
  test_class: ''
  test_function: test_convert_to_base_unit
  fixtures: []
  markers: []
notes:
  behavior: Converts sensor values to base units across device classes.
  redundancy: Core conversion logic coverage.
  decision_rationale: Keep. Base unit conversion is foundational.
---

# Behavior summary

Validates conversion of values to base units for power, energy, and other device classes.

# Redundancy / overlap

No overlap with base unit mapping tests.

# Decision rationale

Keep. Protects conversion behavior.

# Fixtures / setup

None.

# Next actions

None.
