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
  nodeid: tests/test_init.py::test_setup_reentry_after_timeout_failure
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_setup_reentry_after_timeout_failure
  fixtures: []
  markers: []
notes:
  behavior: Second setup attempt succeeds after a timeout failure, indicating cleanup correctness.
  redundancy: Distinct from basic timeout test; validates cleanup path.
  decision_rationale: Keep. Ensures retry behavior works after failure.
---

# Behavior summary

Forces a timeout on first setup, then retries with a working coordinator and asserts success.

# Redundancy / overlap

No overlap with simple timeout test; adds retry/cleanup coverage.

# Decision rationale

Keep. Important cleanup/retry validation.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

None.
