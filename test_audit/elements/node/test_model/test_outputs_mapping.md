---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: Node with power balance
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/elements/node/test_model.py::test_outputs_mapping
  source_file: tests/elements/node/test_model.py
  test_class: ''
  test_function: test_outputs_mapping
  fixtures: []
  markers: []
notes:
  behavior: Maps node power balance output to node device output.
  redundancy: Element output mapping tests are standard but element-specific.
  decision_rationale: Keep. Ensures node output mapping.
---

# Behavior summary

Transforms model power balance output into node sensor output.

# Redundancy / overlap

Pattern exists across elements but content is node-specific.

# Decision rationale

Keep. Protects output mapping.

# Fixtures / setup

Uses element registry and output data.

# Next actions

None.
