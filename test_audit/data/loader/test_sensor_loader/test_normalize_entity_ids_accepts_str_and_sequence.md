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
  nodeid: tests/data/loader/test_sensor_loader.py::test_normalize_entity_ids_accepts_str_and_sequence
  source_file: tests/data/loader/test_sensor_loader.py
  test_class: ''
  test_function: test_normalize_entity_ids_accepts_str_and_sequence
  fixtures: []
  markers: []
notes:
  behavior: Normalizes string and list inputs to entity ID lists and rejects invalid types.
  redundancy: Unique normalization behavior.
  decision_rationale: Keep. Entity ID normalization is fundamental.
---

# Behavior summary

Normalization supports strings and sequences and rejects invalid types.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures entity ID normalization.

# Fixtures / setup

None.

# Next actions

None.
