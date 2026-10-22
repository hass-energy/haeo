# Testing

HAEO uses pytest, and Codecov requires coverage of the lines each pull request changes.

For more information on testing Home Assistant integrations, see:

- [Testing integrations documentation](https://developers.home-assistant.io/docs/development_testing/)
- [pytest fixtures reference](https://developers.home-assistant.io/docs/development_testing/#test-fixtures)

## Test organization

Tests are colocated with source code in `tests/` subdirectories within each package, such as `core/model/tests/`, `core/adapters/elements/tests/`, `flows/elements/tests/`, and `flows/tests/`.
The top-level `tests/` directory holds only scenario tests, guide tests, and tests of the developer CLIs in `tools/`.

The root [`conftest.py`](https://github.com/hass-energy/haeo/blob/main/conftest.py) holds the shared fixtures and registers the runtime translation checker plugin.

Tests run with `filterwarnings = ["error"]`, so a new warning fails the test.

## Test structure

**Unit tests**: Fast, isolated verification of element constraints, cost functions, data validation

**Integration tests**: Coordinator data flow, sensor updates, config entry lifecycle

**Scenario tests**: Complete systems with realistic data captured from users' diagnostics

## Local Home Assistant simulation

Use `uv run sim` to boot a live Home Assistant instance with time-shifted scenario inputs for interactive testing.
This is the recommended way to explore HAEO behavior with realistic forecast and price data.

```bash
uv run sim scenario1
uv run sim scenario1 --interval 30 --speed 60
uv run sim scenario1 --no-config
```

See [Local simulation](local-sim.md) for full options and architecture.

## Scenario testing

Scenario tests verify complete system integration with realistic Home Assistant data.
`tests/scenarios/test_scenarios.py` discovers every `scenario*/` folder that holds the four files below and runs it as one parametrized case.

### Structure

Each scenario folder contains:

- `config.json` - The hub's configuration with its element subentries
- `environment.json` - The captured environment, including `optimization_start_time` and `timezone`
- `inputs.json` - The Home Assistant entity states HAEO read
- `outputs.json` - The expected output sensors, which is the scenario's snapshot

### Running scenario tests

```bash
# Run all scenarios
uv run pytest -m scenario

# Run specific scenario
uv run pytest "tests/scenarios/test_scenarios.py::test_scenarios[scenario1]" -m scenario

# Update outputs.json after an intended change
uv run pytest -m scenario --snapshot-update
```

pytest's configuration selects no markers, so a plain `uv run pytest` runs scenario, guide, and benchmark tests too.
The `test` gate in `tools/check.py` deselects them with `-m "not guide and not scenario and not benchmark"`, and scenarios run as their own gate in `uv run check` and their own job in CI.

### Test behavior

- Freezes time at the scenario's `optimization_start_time` in its `timezone`
- Compares every output sensor with `outputs.json` through a custom syrupy extension that writes the snapshot as JSON
- Generates visualizations in each scenario's `visualizations/` directory

For detailed scenario setup instructions, see [`tests/scenarios/README.md`](https://github.com/hass-energy/haeo/blob/main/tests/scenarios/README.md).

## Model element testing

Model element tests use structured test data in `core/model/tests/test_data/`.
Each module there defines `VALID_CASES` for one kind of model element or segment.
`test_data/__init__.py` aggregates them into lists such as `VALID_ELEMENT_CASES` and `VALID_CONNECTION_CASES`, which the parametrized tests in `core/model/elements/tests/` and `core/model/elements/segments/tests/` run.

Each element case is an `ElementTestCase` (defined in `test_data/element_types.py`) holding:

- `factory`: The model element class or a function that builds one
- `data`: The keyword arguments passed to the factory
- `inputs`: Optional power fixes, bounds, and costs that drive the element in a small optimization
- `expected_outputs` and `expected_cost`: What the solved element reports

## Adapter mapping tests

Each element type's adapter is tested through mapping cases in `core/adapters/elements/tests/test_data/<element_type>.py`.
Each module defines `CREATE_CASES`, pairing a loaded config with the model elements `model_elements()` builds, and `OUTPUTS_CASES`, pairing model outputs with the device outputs `outputs()` maps them to.
The modules are found through the `ELEMENT_TYPES` registry, so a registered type without a module fails collection, and `test_mapping.py` checks that every type has at least one case of each kind.
Behavior that the mapping cases cannot show gets its own test in `core/adapters/elements/tests/test_<element_type>.py`.

## Flow and schema tests

Each element type has flow test data in `flows/tests/test_data/<element_type>.py`.
`VALID_DATA` holds configurations in the shape stored in the subentry, and `INVALID_DATA` holds inputs the flow must reject.
The shared tests in `flows/tests/test_element_flows.py` run against every registered element type, and schema tests such as `elements/tests/test_init.py` validate each `VALID_DATA` configuration against its element type's schema.
Element-specific flow behavior is tested in `flows/elements/tests/test_<element_type>_flow.py`.

When adding an element type, register its adapter in `ELEMENT_TYPES` in [`core/adapters/registry.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/adapters/registry.py) and add both test data modules.
The parametrized tests then include it.

## Translation checks

The runtime translation checker in [`translations/tests/runtime_checks.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/translations/tests/runtime_checks.py) is a pytest plugin that fails a test when HAEO shows a string `en.json` does not translate.
It checks flow forms, aborts, repair issues, Home Assistant errors raised with a HAEO translation key, entity names, and enum sensor states as each is shown, and that every placeholder a string uses is supplied.
`translations/tests/test_translations.py` checks the other direction: every key the integration uses is present and no key is unused.
Tests therefore use the real translation keys rather than invented ones.

## Type safety over defensive tests

HAEO uses Python's type system to make certain error conditions impossible, rather than writing tests for defensive error logging.
Conditions guaranteed by architectural constraints, such as data validated at the config flow boundary, are accessed directly, so a violation raises as the programming error it is.
Defensive checks and their tests belong where the data comes from outside: forecast parsers, Home Assistant state, user input, and solver failures.
See the [typing guide](typing.md) for the patterns.

## Guide testing

Guide tests verify the interactive walkthroughs by executing them against a live Home Assistant instance using Playwright.
Each walkthrough's `guide` code blocks are extracted from the markdown source, executed in order, and screenshots are captured for documentation.

### How it works

Walkthrough pages in `docs/walkthroughs/` contain `guide` fenced code blocks that call primitives defined in `tests/guides/primitives/`.
The guide runner (`tools/guide_runner.py`) extracts these blocks, executes them sequentially against a live HA instance, and captures screenshots into per-block directories.
Consecutive blocks share the same browser and HA context so state accumulates across steps.

The instance loads the input states of the scenario `SCENARIO_DIR` in `tools/guide_runner.py` names, and the clock stands still at that scenario's `optimization_start_time` for the whole run.
Home Assistant's wall clock is frozen while its event loop keeps real time, so timers still fire, and each browser context is pinned to the same instant.
Every capture therefore shows the same horizon however slowly the run goes.

Each guide runs once, and every capture is saved in both themes: the page is captured in the theme it shows, then switched to the other with Home Assistant's own theme setting and captured again.

Before every screenshot the pointer moves off the page and the capture waits for the page to settle (`tests/guides/primitives/js/wait_settled.js`).
Settling waits on signals the page gives rather than on time: HTTP and websocket requests being answered, custom elements being defined, Lit updates completing, images on screen loading, icons, ripples and dialogs finishing, and an animation frame passing with no change to the DOM.
Animations and transitions are finished on the spot.
A page that has not settled within ten seconds fails the guide, naming what it was still waiting for.

Primitives never sleep for a fixed time.
After an action, they wait for the condition that shows it took effect, such as a URL, an attribute, or a dialog appearing.
After a change to the configuration, `expect_config_reload` waits for the reload and then brings the frontend up to date with Home Assistant, so counts of devices and entities are current.

A `guide-setup` block can start from where another walkthrough ends with `run_guide("name")`.
The first guide in a run to need that walkthrough replays it without screenshots, then saves Home Assistant's config directory.
Every later one restores the saved directory instead of replaying, which takes a fraction of the time.
Either way Home Assistant restarts from the saved state, and the page loads the app and moves within it to where the walkthrough ended.
Only what Home Assistant stores carries over, so `run_guide` comes first in a guide, and a walkthrough used this way leaves its state in Home Assistant's storage rather than in states set directly.
Guides running in parallel share the saved directories for the length of one run.

### Showing the plan

Guides can show what HAEO plans, not only how to configure it.
The card primitives in `tests/guides/primitives/cards.py` render the integration's own Lovelace cards from the live instance's data and save them as SVG figures:

- `show_forecast_card(page, hass, step=..., elements=[...])` re-runs the optimizer and captures the forecast card showing those elements' plans.
    Pass `inputs=[...]` to also show some elements' input forecasts, such as a solar forecast next to the solar HAEO plans to use, and `horizon` to choose how much of the forecast to show.
- `show_topology_card(page, hass, step=...)` captures the topology card.
- `set_input(hass, element=..., field=..., value=...)` changes an input entity, as a user would from a dashboard, so the next card shows what the change does.
- `set_policy_rule(hass, rule=..., enabled=...)` turns a policy rule on or off with its enabled switch.

The cards load from the bundles the integration serves, on a page of their own in Home Assistant's default theme, once for each theme.
Each figure carries the card's own markup and styles inside the SVG, so it stays sharp at any size, legend included.
Rebuild the bundles with `npm run build` in `frontend/haeo-forecast-card` after changing the cards, so guides show the current version.

Figures stand apart from the screenshots of configuring HAEO.
A block's screenshots form a slideshow that starts with the last screenshot of the closest earlier block that has one, while its figures follow on their own and never carry over.
When a block saves several figures, readers flick between them with arrows, which suits comparing variants of a plan: change inputs with `set_input` between captures in one block.

Screenshots are content-hash cached: a `manifest.json` maps each block's content hash to its screenshot directory.
If a block's content hasn't changed, its screenshots are reused without re-running.

### Running guide tests

```bash
# Run all guide tests in parallel
uv run pytest -m guide -n 8 --timeout=300

# Run one walkthrough sequentially with the guide runner CLI
uv run python -m tools.guide_runner docs/walkthroughs/sigenergy-system.md
```

Guide tests carry the `guide` marker; the `test` gate deselects them and `uv run check` runs them only when asked, with `uv run check guide`.
They need a live Home Assistant instance (started automatically by the test fixtures) and Playwright Firefox.

### CI integration

Guide tests run in two CI workflows:

- **Guides workflow** (`guides.yml`): Runs on push, PR, and merge group to validate guide correctness
- **Docs workflow** (`docs.yml`): Generates screenshots and optimizes them with optipng before building documentation for deployment

### Screenshot rendering

During documentation build, `tools/guide_fence.py` acts as a custom `pymdownx.superfences` formatter.
It reads the manifest files and renders each guide block as an interactive screenshot slideshow.
The slideshow frontend is implemented in `docs/javascripts/guide-slideshow.js` with styling in `docs/stylesheets/guide.css`.

## CI requirements

All PRs must pass every CI gate, including unit and scenario tests, Ruff, Pyright, and the documentation build.
`uv run check` runs every gate that can run locally.
Codecov requires coverage of the changed lines.

## Related documentation

<div class="grid cards" markdown>

- :material-sitemap:{ .lg .middle } **Architecture**

    ---

    System design overview.

    [:material-arrow-right: Architecture guide](architecture.md)

- :material-network:{ .lg .middle } **Energy models**

    ---

    Model implementation details.

    [:material-arrow-right: Energy models](energy-models.md)

- :material-sync:{ .lg .middle } **Coordinator**

    ---

    Update cycle patterns.

    [:material-arrow-right: Coordinator guide](coordinator.md)

- :material-database:{ .lg .middle } **Data loading**

    ---

    Loader testing approaches.

    [:material-arrow-right: Data loading guide](data-loading.md)

- :material-cog:{ .lg .middle } **Config flow**

    ---

    Flow testing patterns.

    [:material-arrow-right: Config flow guide](config-flow.md)

- :material-hammer-wrench:{ .lg .middle } **Setup**

    ---

    Environment setup for development.

    [:material-arrow-right: Setup guide](setup.md)

</div>
