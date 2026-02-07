---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
meta:
  source_file: /Users/trenthouliston/Code/gaeo/tests/model/conftest.py
  fixtures:
    - solver
notes:
  behavior: Provides a HiGHS solver fixture with output suppressed for model tests.
  redundancy: No redundancy; model tests rely on a quiet solver instance.
  decision_rationale: Keep. Centralized solver configuration avoids duplicated setup.
---

# Fixture summary

Defines a solver fixture returning a configured HiGHS instance.

# Usage and scope

- solver: used by model tests to avoid repeated solver configuration.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Fixture is essential for model tests.

# Next actions

None.
