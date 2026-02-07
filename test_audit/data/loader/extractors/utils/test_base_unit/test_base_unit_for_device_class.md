---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: power-kW
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: energy-kWh
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: energy_storage-kWh
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: temperature-None
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: humidity-None
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: pressure-None
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: None-None
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/data/loader/extractors/utils/test_base_unit.py::test_base_unit_for_device_class
  source_file: tests/data/loader/extractors/utils/test_base_unit.py
  test_class: ''
  test_function: test_base_unit_for_device_class
  fixtures: []
  markers: []
notes:
  behavior: Maps device classes to base units or None.
  redundancy: Unique mapping behavior.
  decision_rationale: Keep. Base unit mapping is foundational.
---

# Behavior summary

Device class mapping returns expected base units.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures base unit mapping.

# Fixtures / setup

None.

# Next actions

None.
