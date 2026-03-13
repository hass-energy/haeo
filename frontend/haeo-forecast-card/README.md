# HAEO forecast card frontend

This package builds the `haeo-forecast-card` Lovelace custom card bundle.

## Commands

- `npm run build` builds `custom_components/haeo/www/haeo-forecast-card.js`.
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

## Test data strategy

Behavioral tests use real HAEO scenario outputs from `tests/scenarios/*/outputs.json`.
This keeps the frontend ingestion model aligned with real integration payloads.
