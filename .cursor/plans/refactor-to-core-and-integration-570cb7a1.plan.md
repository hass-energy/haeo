<!-- 570cb7a1-28ff-4235-aa7f-7014a1d14a4a ebab34d3-d688-4f41-a741-fac16f400cfe -->
# Extract Model to haeo_core Library

This plan extracts the model code into a standalone library named `haeo_core` to avoid namespace conflicts with the Home Assistant integration.

## 1. Library Setup (`haeo_core/`)

- [ ] Create directory `haeo_core` at repository root
- [ ] Create `haeo_core/__init__.py` (make it a package)
- [ ] Create `haeo_core/pyproject.toml`
- Name: `haeo-core`
- Dependencies: `numpy`, `pulp`
- Build system: `setuptools`

## 2. Code Migration

- [ ] Move `custom_components/haeo/model/` contents to `haeo_core/model/`
- Ensure `haeo_core/model/__init__.py` exists
- [ ] Create `haeo_core/tests/`
- [ ] Move pure unit tests from `tests/model/` to `haeo_core/tests/`
- Exclude `test_scenarios.py` (depends on HA)

## 3. Refactoring Imports

- [ ] Update internal library imports (inside `haeo_core`) to use relative imports or `haeo_core` prefix.
- [ ] Update integration code (`custom_components/haeo`) to import from `haeo_core.model`.
- [ ] Update tests to import from `haeo_core.model`.

## 4. Cleanup

- [ ] Remove empty `custom_components/haeo/model` directory.
- [ ] Remove moved tests from `tests/model`.

## 5. Verification

- [ ] Run `pytest haeo_core/tests` to verify library integrity.
- [ ] (Optional) Run integration tests to verify integration with new library (requires library installation or PYTHONPATH update).

### To-dos

- [ ] Create core directory structure and pyproject.toml
- [ ] Move model code to core/haeo/core/model
- [ ] Move unit tests to core/tests
- [ ] Create integration directory and move custom_components
- [ ] Move remaining tests to integration/tests
- [ ] Update imports in core and integration
- [ ] Verify core tests pass
- [ ] Verify integration tests pass