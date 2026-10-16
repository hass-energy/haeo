# HAEO forecast card frontend

This package builds the HAEO Lovelace custom card bundles with [Rolldown](https://rolldown.rs/) (Rollup-compatible bundler with tree-shaking and minification).

## Commands

- `npm run build` builds the card bundles into `custom_components/haeo/www/` via Rolldown.
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

- **Bundler**: Rolldown (`rolldown.config.mjs`) with ESM output and minification.
- **Independent bundles**: each card is built and registered as its own Lovelace resource, so a stale or missing copy of one card can never break registration of the other.
- **Instant registration via thin entry + lazy controller**: Home Assistant only guarantees a custom card through `customElements.whenDefined` plus a short timeout, so gating `customElements.define` behind a large dependency graph causes the intermittent "Custom element doesn't exist" race. Each card's registered entry (`haeo-forecast-card.entry.<hash>.js`, `haeo-topology-card.entry.<hash>.js`, ~5 KB each) contains only the element class and its registration, with no heavy imports, so registration happens immediately regardless of bundle size or network speed. The heavy rendering stack (preact, MobX, ELK) lives in a lazily-imported controller chunk (`haeo-forecast-card.forecast-card-controller.<hash>.js` ~130 KB, `haeo-topology-card.topology-card-controller.<hash>.js` with ELK ~1.4 MB) loaded on first use.
- **Content-hashed filenames**: every emitted filename carries a content hash and is prefixed per card, so the integration serves them with long-lived cache headers and no URL survives a rebuild to serve a stale copy. The integration finds each entry on disk by its `.entry.` marker.
- **Tree-shaking**: unused dependency exports are dropped; app modules keep side-effect imports (`customElements.define`, CSS).
- **Node helper**: `dist/render-topology-svg.mjs` is built in the same Rolldown config for SVG export scripts.

## Test data strategy

Behavioral tests use real HAEO scenario outputs from `tests/scenarios/*/outputs.json`.
This keeps the frontend ingestion model aligned with real integration payloads.
