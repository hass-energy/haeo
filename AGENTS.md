# AGENTS.md

Guidance for AI agents working in the HAEO repository.

## Cursor Cloud specific instructions

HAEO is a **Home Assistant custom integration** — there is no standalone app server to start. Development and verification run through **pytest** with in-process Home Assistant.

### Environment

- **Python 3.13+** is managed by `uv` (`.venv/`). Ensure `$HOME/.local/bin` is on `PATH` for the `uv` binary.
- **Node.js** is required for Prettier (root `npm ci`) and for the forecast card / scenario visualizations.

### Common commands

| Task | Command |
|------|---------|
| Install Python deps | `uv sync --locked --all-extras --dev` |
| Install JS deps (Prettier) | `npm ci` |
| Install forecast card deps | `npm --prefix frontend/haeo-forecast-card ci` |
| Build forecast card | `npm --prefix frontend/haeo-forecast-card run build` |
| Lint (Python) | `uv run ruff check` / `uv run ruff format --check` |
| Typecheck | `uv run pyright` |
| Architecture boundaries | `uv run lint-imports` |
| Default test suite (CI) | `uv run pytest -m "not guide and not scenario and not benchmark"` |
| Scenario E2E tests | `uv run pytest tests/scenarios/test_scenarios.py -m scenario` |
| Guide/walkthrough tests | `uv run pytest -m guide -v --timeout=300` (needs Playwright: `uv run playwright install --with-deps firefox`) |
| Docs preview | `uv run mkdocs serve` → http://127.0.0.1:8000 |

### Gotchas

- **Scenario tests** generate SVG visualizations and require the forecast card built (`npm --prefix frontend/haeo-forecast-card run build`). Without it, scenario tests fail with missing `render-topology-svg.mjs` or jsdom errors.
- **No external Home Assistant** is needed for automated tests; `pytest-homeassistant-custom-component` spins up HA in-process.
- **Manual E2E** requires copying/symlinking `custom_components/haeo` into a real HA config and restarting HA — not part of routine cloud-agent setup.
- The **`diag` CLI** (`uv run diag --file path/`) runs optimization offline from diagnostics exports; scenario folders use a split JSON format that may not match all diag code paths.

See [docs/developer-guide/setup.md](docs/developer-guide/setup.md) and [CONTRIBUTING.md](CONTRIBUTING.md) for full contributor documentation.
