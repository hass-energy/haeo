---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: Connection with all optional fields
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: Connection without optional fields
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/elements/connection/test_model.py::test_outputs_mapping
  source_file: tests/elements/connection/test_model.py
  test_class: ''
  test_function: test_outputs_mapping
  fixtures: []
  markers: []
notes:
  behavior: Maps connection model outputs to device outputs with optional shadows.
  redundancy: Core output mapping coverage.
  decision_rationale: Keep. Output mapping is critical.
---

# Behavior summary

Parameterized test validates connection output mapping.

# Redundancy / overlap

No overlap with model element creation.

# Decision rationale

Keep. Output mapping is central.

# Fixtures / setup

Uses parameterized cases.

# Next actions

None.
