---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
meta:
  source_file: /Users/trenthouliston/Code/gaeo/tests/scenarios/conftest.py
  fixtures:
    - expand_diagnostics_scenario
    - scenario_path
    - scenario_data
    - snapshot
notes:
  behavior: Provides scenario data loading, migration, and snapshot extension fixtures for scenario tests.
  redundancy: Scenario-only; no overlap with non-scenario tests.
  decision_rationale: Keep. These fixtures are required for scenario test infrastructure even though scenarios are out of scope for this audit.
---

# Fixture summary

Defines fixtures to migrate scenario diagnostics, load scenario data, and customize snapshots.

# Usage and scope

Scenario-only fixtures; scenario tests are excluded from this audit but fixtures remain valid.

# Redundancy / overlap

No redundancy in non-scenario suite.

# Decision rationale

Keep. Scenario testing relies on these fixtures.

# Next actions

None.
