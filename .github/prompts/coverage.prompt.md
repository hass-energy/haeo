---
description: Check code coverage and identify untested code that needs test cases
---

# Code Coverage Analysis

Check code coverage for the current branch and identify areas that need additional test cases.

## Step 1: Run Coverage Analysis

### Full Coverage Report

```bash
uv run pytest --cov=custom_components/haeo --cov-branch --cov-report=term-missing
```

This provides:

- Overall coverage percentage
- Branch coverage
- Line-by-line coverage with missing lines identified

### HTML Coverage Report

For detailed visual analysis:

```bash
uv run pytest --cov=custom_components/haeo --cov-branch --cov-report=html
```

Open `htmlcov/index.html` in a browser to see:

- File-by-file coverage
- Line-by-line highlighting
- Branch coverage visualization

### Coverage for Changed Files Only

To focus on changes in the current branch:

```bash
# Get list of changed Python files
git diff main...HEAD --name-only --diff-filter=AM | grep '\.py$' | grep -E '^(custom_components|tests)/' | grep -v '^tests/'

# Run coverage for changed files only
uv run pytest --cov=custom_components/haeo --cov-branch --cov-report=term-missing $(git diff main...HEAD --name-only --diff-filter=AM | grep '\.py$' | grep -E '^custom_components/' | tr '\n' ' ')
```

## Step 2: Analyze Coverage Results

### Coverage Requirements

- **CI Requirement**: Coverage ≥ 95% overall
- **Codecov Enforcement**: Coverage must not decrease from main on changed lines
- **Focus**: Test behavior and edge cases, not arbitrary percentages

### Identify Missing Coverage

For each file with low coverage:

1. **Review untested lines**: Check which lines are not covered

2. **Consider simplification first**: Before adding test cases, evaluate if the code can be simplified:

    - **Simplify logic**: If possible, refactor to remove unnecessary branches and conditional paths
    - **Reduce complexity**: Simpler code with fewer branches is easier to test and maintain
    - **Prefer simplification over testing**: Removing code that needs testing is better than adding tests for complex logic
    - **Example**: Instead of testing multiple conditional branches, refactor to use a single, simpler approach

3. **Determine if coverage is needed**:

    - **Unreachable code**: If lines cannot be covered by exercising input data, they may be unreachable and should be removed
    - **Edge cases**: Missing coverage often indicates untested edge cases
    - **Error paths**: Ensure error handling is tested
    - **Branch coverage**: Check that both true/false branches of conditionals are tested

4. **Prioritize by importance**:

    - Critical business logic (optimization, constraints, cost functions)
    - Error handling paths
    - Edge cases and boundary conditions
    - New features added in this branch

## Step 3: Add Test Cases

### Test Style Guidelines

Follow HAEO testing standards from `.github/instructions/tests.instructions.md`:

- **Function-style tests**: Use `def test_...()` not class-based tests
- **Parametrized tests**: Use `@pytest.mark.parametrize` for data-driven tests
- **Test data modules**: Add cases to `tests/model/test_data/` for model element tests
- **Direct property access**: Access properties directly without None checks when you've created the entities

### Where to Add Tests

1. **Model elements**: Add test cases to `tests/model/test_data/{element}_cases.py`

    - Add to `VALID_CASES` or `INVALID_CASES` lists
    - Cases are aggregated in `__init__.py` for parametrized tests

2. **Element adapters**: Add tests to `tests/elements/{element_type}/test_adapter.py`

3. **Config flows**: Add test data to `tests/flows/test_data/`

4. **Coordinator/data loading**: Add tests to `tests/test_coordinator.py` or `tests/test_data_loading.py`

5. **New functionality**: Create appropriate test files following existing patterns

### Example: Adding Model Element Test Cases

```python
# In tests/model/test_data/battery_cases.py
VALID_CASES = [
    # ... existing cases ...
    {
        "description": "Battery at minimum SOC with zero power",
        "factory": create_battery,
        "data": {"capacity": 10.0, "soc_min": 0.2, "soc_max": 0.9},
        "expected_outputs": {...},
    },
]
```

## Step 4: Verify Coverage Improvement

After adding tests:

1. **Re-run coverage**:

    ```bash
    uv run pytest --cov=custom_components/haeo --cov-branch --cov-report=term-missing
    ```

2. **Check coverage for changed lines**:

    - Ensure new code has adequate coverage
    - Verify coverage hasn't decreased for modified code
    - **Note**: Codecov may report changed lines that are not directly part of your changeset due to indirect changes (e.g., refactoring that affects other code paths, or changes in dependencies that trigger different execution paths)

3. **Run tests to ensure they pass**:

    ```bash
    uv run pytest
    ```

## Step 5: Summary

Provide a summary of:

- Current overall coverage percentage
- Coverage for changed files (if applicable)
- Files with low coverage that need attention
- Test cases added to improve coverage
- Any unreachable code identified
- Confirmation that coverage requirements are met

## Notes

- **Coverage philosophy**: Focus on testing behavior and edge cases, not achieving arbitrary percentages
- **Simplification preferred**: When encountering untested code, first consider if the logic can be simplified to remove branches and lines that need testing
- **Codecov**: Enforces that coverage does not decrease from main on changed lines
- **Indirect changes**: Codecov may report changed lines that are not directly part of your changeset due to indirect changes (refactoring effects, dependency changes, or different execution paths)
- **Unreachable code**: If lines cannot be covered by exercising input data, they may be unreachable and should be removed
- **Branch coverage**: Use `--cov-branch` to ensure both branches of conditionals are tested
- **CI requirement**: Overall coverage must be ≥ 95%
- **Changed lines**: Codecov focuses on coverage of changed lines, not overall project coverage
