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
  nodeid: tests/data/loader/test_constant_loader.py::test_constant_loader_float_conversion
  source_file: tests/data/loader/test_constant_loader.py
  test_class: ''
  test_function: test_constant_loader_float_conversion
  fixtures: []
  markers: []
notes:
  behavior: Converts ints to floats and preserves float values for float loader.
  redundancy: Unique conversion behavior.
  decision_rationale: Keep. Ensures float normalization.
---

# Behavior summary

Float loader converts ints to floats and keeps floats unchanged.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Conversion behavior is critical.

# Fixtures / setup

None.

# Next actions

None.
