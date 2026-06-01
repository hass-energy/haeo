# HAEO forecast card frontend

This package builds the `haeo-forecast-card` Lovelace custom card bundle with [Rolldown](https://rolldown.rs/) (Rollup-compatible bundler with tree-shaking, code splitting, and minification).

## Commands

- `npm run build` builds `custom_components/haeo/www/haeo-forecast-card.min.js` (and lazy-loaded chunks) via Rolldown.
- `npm run dev` watches and rebuilds during frontend work.
- `npm run test` runs frontend unit and smoke tests.
- `npm run test:coverage` runs tests with coverage reports and threshold enforcement.
- `npm run typecheck` runs strict TypeScript checks.
- `npm run lint` runs ESLint.
- `npm run format` runs Prettier format checks.
- `npm run check` runs the full quality gate (`typecheck`, `lint`, `format`, coverage tests).
- `npm run storybook` runs isolated component stories.
- `npm run build-storybook` builds static Storybook output.
- `npm run preview:svg` exports an actual rendered card SVG preview to `previews/card-preview.svg`.

## Bundling

- **Bundler**: Rolldown (`rolldown.config.mjs`) with ESM output, minification, and code splitting.
- **Forecast card entry**: ~130 KB initial load; topology/ELK loads lazily from `/haeo-static/` chunks.
- **Tree-shaking**: unused dependency exports are dropped; app modules keep side-effect imports (`customElements.define`, CSS).
- **Node helper**: `dist/render-topology-svg.mjs` is built in the same Rolldown config for SVG export scripts.

## Test data strategy

Behavioral tests use real HAEO scenario outputs from `tests/scenarios/*/outputs.json`.
This keeps the frontend ingestion model aligned with real integration payloads.
