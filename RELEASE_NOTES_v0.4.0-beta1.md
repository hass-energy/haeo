# HAEO v0.4.0-beta1

> **Pre-release** — this is a beta for testing before the stable v0.4.0 release.

> [!CAUTION]
> **Back up your Home Assistant configuration before upgrading.** This release includes one-way schema migrations (v1.3 → v1.4) that restructure your element configuration data. Once migrated, **you cannot downgrade back to v0.3.x** without restoring a backup.
>
> **What could go wrong:**
>
> - Battery discharge wear costs and charge incentives are moved into a new Policies element. If the migration misinterprets a pricing value (particularly entity-based charge incentives), the optimizer may treat an incentive as a cost or vice versa.
> - Connections are restructured from bidirectional to unidirectional. If a bidirectional connection had asymmetric settings, the split may not perfectly preserve both directions.
> - All config values change storage format (raw values → typed objects). External tools or automations that read HAEO config entry data directly will break.
>
> **Recommended steps:** Take a full Home Assistant backup, upgrade, then check Settings → Devices & Services → HAEO to verify your elements and the new Policies subentry look correct. Check the Home Assistant log for any migration warnings.

## Highlights

- ⚡ **Power policies** — define per-source pricing rules so the optimizer knows that solar exports earn feed-in tariffs while battery exports incur wear costs
- 🎯 **Deterministic optimization** — new calibrated multiobjective solver eliminates random tie-breaking, giving consistent dispatch schedules every run
- 🔋 **Sheddable loads & battery salvage value** — loads can now be curtailed when economically justified, and batteries value their remaining stored energy at the horizon end
- 🌍 **Automatic currency detection** — HAEO reads your price sensor units and displays the correct currency symbol without configuration

## ⚠️ Breaking Changes

### Pricing moves to power policies

Battery discharge wear costs, charge incentives, and solar production costs have moved from individual element configuration into the new **Power Policy** element. Existing configurations are **migrated automatically** (schema v1.3 → v1.4), but you should verify your policies after upgrading:

1. Open HAEO settings → you should see a new "Policies" subentry
2. Confirm the migrated rules match your previous pricing
3. Battery charge incentive prices are negated during migration (positive stored value → negative policy price) to preserve the original incentive semantics

If you had entity-based (non-constant) charge incentive prices, check the Home Assistant log for a migration warning — you may need to create a negating template sensor.

### Connection model is now unidirectional

Connections are now explicitly directional (source → target). Bidirectional connections use two separate connection entries. Existing bidirectional connections are migrated automatically, but verify that import/export paths are configured correctly after upgrading.

### Configuration data format change

Element configuration now stores values as typed objects (`{"type": "entity", "value": [...]}` / `{"type": "constant", "value": 0.5}`) instead of raw values. This is migrated automatically — no action required — but any external tools reading config entry data directly will need updating.

## User-Facing Changes

### New Features

- **Power policy element** — define directional pricing rules with source/target matching and wildcard support (#369)
- **Sheddable loads** — mark loads as curtailable so the optimizer can shed them when cost-effective (#303)
- **Battery salvage value** — assign a terminal value ($/kWh) to stored energy, discouraging unnecessary end-of-horizon discharge (#302)
- **Nordpool integration** — automatic extraction of energy pricing from Nordpool `raw_today`/`raw_tomorrow` sensor attributes (#367)
- **Lexicographic multiobjective optimization** — three solver modes (lexicographic, blended, calibrated) for deterministic time-preference tie-breaking (#301)
- **Last run timestamp** — optimization status sensor now includes a `last_run` attribute showing when the optimizer last completed (#381)

### Configuration Improvements

- **Grouped UI sections** — config flows now organize fields into collapsible sections for easier navigation (#266)
- **Automatic currency symbol detection** — reads currency from your price sensor units; falls back to HA config currency (#368)
- **Policy source/target filtering** — policy config flow only shows elements that can actually source or sink power (e.g., solar appears as source only, load as target only) (#380)
- **Policy rule context in sensors** — policy price input numbers now expose sibling fields (source, target, rule name) in state attributes (#377)

### Bug Fixes

- Fix optimizer crash when optional efficiency field is unset or cleared (#360)
- Fix battery power limits and efficiency segment ordering (#297)
- Fix connection segment ordering for directional flows (#299)
- Fix network period tracking across optimization runs (#295)
- Fix recorder forecast filtering dropping valid entries (#310)
- Fix participant name resolution after Home Assistant restart — deserialized strings are now converted to ElementType (#373)
- Fix optimizer re-run race condition when updating subentry values concurrently (#375)
- Fix battery charge incentive price sign in v1.4 migration (#376)
- Fix policy compilation blocking unpolicied flows — changed from default-deny to default-allow so flows without explicit policies pass freely (#379)
- Fix policy endpoint restore values rendering as `[object Object]` in the UI (#383, #384)
- Fix policy edit flow not preserving existing source/target when fields are omitted (#382)
- Require explicit `enabled` and `price` on policy rules; backfill missing fields during v1.4 migration (#385)
- Remove null values from horizon sensor attributes (#348)

## Developer-Facing Changes

### Developer Highlights

The entire optimization engine has been extracted into a **standalone `core/` package** with zero Home Assistant dependencies. This is the largest architectural change since HAEO's initial release — 20+ PRs restructured the codebase into clean layers that can be tested, debugged, and eventually distributed independently of Home Assistant.

### Architecture

- **Core package extraction** — model, schema, adapters, and data loading moved to `custom_components/haeo/core/` with enforced import boundaries (#312–#340)
- **Three-layer architecture** — device layer (elements/) → adapter layer (core/adapters/) → model layer (core/model/) with clear data flow
- **Import linter** — enforces that `core/` has no Home Assistant imports (#320)
- **Unidirectional connections with functional segment composition** — segments compose as expression chains rather than using auxiliary linking variables (#364)
- **Tag infrastructure** — power flow tagging system enables per-source tracking through the network graph (#370)
- **Policy compilation pipeline** — 8-step compilation from policy rules to tagged connection costs: flow enumeration → signature computation → VLAN assignment → reachability analysis → connection tagging → source tags → access lists → pricing injection; default-allow model for unpolicied flows (#369, #379)
- **Element capability metadata** — `can_source` / `can_sink` on element adapters for filtering policy participants (#380)
- **OptimizationContext** — immutable frozen dataclass capturing all optimization inputs for reproducible diagnostics (#291, #305)
- **StateMachine protocol** — minimal interface isolating model from Home Assistant state access (#314)
- **ElementType enum** — single StrEnum for all element types replacing string literals (#319)

### Schema/API Changes

- **Object-based config storage** — values stored as discriminated TypedDicts (`EntityValue`, `ConstantValue`, `NoneValue`) with type predicates (#296)
- **ListFieldHints** — generic infrastructure for declaring input fields within list-typed config fields (#371)
- **Config loader** — centralized resolution of entity/constant/none values from config data (#338, #339, #342)
- **Enriched schemas** — schemas now carry enough metadata to eliminate adapter `inputs()` methods (#322)
- **Schema migrations formalized** — structured step pipeline with v0.3.3 fixture regression tests (#359)
- **Scalar input support** — data loader handles non-forecast numeric inputs for fields like salvage value (#302)

### Testing & Documentation

- **Tests colocated with source** — test files moved into `tests/` subdirectories within each package (#336)
- **Test audit** — systematic review removing redundant and low-value tests (#300)
- **Literate guide system** — walkthroughs authored as markdown with embedded executable `guide` blocks, automated screenshot generation via Playwright (#139, #345, #365)
- **Diagnostics CLI tool** — offline optimization debugging from saved context (#260)
- **Nordpool data extractor** — pricing extraction from Nordpool HACS integration sensors (#367)

## Contributors

- @TrentHouliston
- @BrendanAnnable
- @purcell-lab 🎉 (first-time contributor!)

## Full Changelog

- Fix zip releases (#386)
- Require enabled and price on policy rules, backfill in v1.4 (#385)
- Fix policy endpoint restore value shape in UI (#384)
- Fix policy endpoint choose restore ordering (#383)
- Fix policy edit defaults and require rule price (#382)
- Add last_run timestamp to optimization status sensor (#381)
- Filter policy source/target by element capability (#380)
- Change policy compilation from default-deny to default-allow (#379)
- Bump version to 0.4.0b1 (#378)
- Add lexicographic multiobjective optimization with calibrated blending (#301)
- Policy config flow UX fixes (#374)
- Negate battery charge incentive price in v1.4 migration (#376)
- Fix optimizer re-run race condition in async_update_subentry_value (#375)
- Expose list item sibling fields in input number extra state attributes (#377)
- Add power policy element with tagged power flow pricing (#369)
- Fix participant name resolution after config entry deserialisation (#373)
- Add ListFieldHints infrastructure for list-typed config fields (#371)
- Add tag infrastructure to model layer (#370)
- Unidirectional connections and functional segment composition (#364)
- Detect currency symbol from user price sensor data (#368)
- Guide tooling infrastructure improvements (#365)
- Add Nordpool energy pricing data extractor (#367)
- Fix optimizer crash when optional efficiency is unset (#360)
- Formalize v0.3.3 migration path validation (#359)
- Remove null values from horizon sensor (#348)
- Fix connection segment ordering (#299)
- Literate guide system with automated screenshot generation (#345)
- Automatically run guides and gather screenshots of the steps (#139)
- Improve config loader types (#342)
- Move context to core (#340)
- Use config loader in coordinator (#339)
- Add config loader (#338)
- Update docs (#337)
- Colocate tests within packages (#336)
- Align tests with source (#335)
- Flatten common sections (#334)
- Move migrations to core schema (#333)
- Move schema consts to core (#332)
- Make diag tool only use core (#331)
- Move more element infra to core (#330)
- Move data to core (#329)
- Make core standalone (#328)
- Add core const (#327)
- Move adapters to core (#326)
- Move schema to core (#325)
- Split sections into core package (#324)
- Move model to core (#323)
- Enrich schema to remove adapter inputs() (#322)
- Fix adapter unit imports (#321)
- Add import linter (#320)
- Add ElementType enum (#319)
- Cleanup elements package (#318)
- Extract adapters from elements (#317)
- Extract flows from elements (#316)
- Extract schema from elements (#315)
- Add StateMachine abstraction (#314)
- Remove ha dt usage (#313)
- Add core package with state and units (#312)
- Fix recorder forecast filtering (#310)
- Add diagnostics CLI tool (#260)
- Normalize SVG clip paths (#307)
- Fix input alignment test (#306)
- Use OptimizationContext for diagnostics (#305)
- Add OptimizationContext (#291)
- Add battery salvage value and scalar inputs (#302)
- Add sheddable loads (#303)
- Run an audit on test files to help remove redundancy/bad tests (#300)
- Swap to using objects to describe the stored data rather than simple values (#296)
- Fix network period tracking (#295)
- Fix battery power limits and efficiency ordering (#297)
- Reuse the group logic that's shared between elements (#293)
- Remove explicit hass injection (#294)
- Update Open-Meteo Solar Forecast link in documentation (#290)
- Add grouped UI sections for config flows (#266)

**Full diff**: [`v0.3.3...v0.4.0-beta1`](https://github.com/hass-energy/haeo/compare/v0.3.3...v0.4.0-beta1)
