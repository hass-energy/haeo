/** Styles for HAEO's selectors, drawn from Home Assistant's theme variables. */
export const SELECTOR_STYLES = `
:host {
  display: block;
  color: var(--primary-text-color);
  font-family: var(--ha-font-family-body, Roboto, sans-serif);
}
.field { display: flex; flex-direction: column; gap: 6px; }
.field.disabled { opacity: 0.6; }
.label { font-size: 0.875rem; color: var(--secondary-text-color); }
.helper { font-size: 0.75rem; color: var(--secondary-text-color); }
.icon { width: 18px; height: 18px; fill: currentColor; flex: none; }
.readout {
  display: inline-flex; flex-direction: column; align-items: center; justify-content: center; flex: none;
  box-sizing: border-box; width: 48px; height: 26px; border-radius: 13px; line-height: 1;
  background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); color: var(--primary-text-color);
}
.readout.fixed { background: color-mix(in srgb, var(--primary-color) 22%, transparent); }
.readout .icon { color: var(--secondary-text-color); }
.readout.add { background: none; }
.readout.add .icon { color: var(--primary-color); }
.readout-value {
  max-width: 44px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  font-size: 0.75rem; font-weight: 500; font-variant-numeric: tabular-nums;
}
.readout-unit {
  max-width: 44px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  font-size: 0.625rem; color: var(--secondary-text-color); margin-top: 1px;
}
.sparkline { width: 40px; height: 18px; overflow: visible; }
.preview-plot { display: flex; align-items: center; gap: 8px; }
.plot { position: relative; flex: 1; min-width: 0; height: 48px; }
.plot svg { display: block; width: 100%; height: 100%; overflow: visible; }
.plot .sparkline-line { stroke-width: 1.5; }
.plot-day { stroke: var(--divider-color); stroke-width: 1; vector-effect: non-scaling-stroke; }
.plot-zero { stroke: var(--divider-color); stroke-dasharray: 3 3; vector-effect: non-scaling-stroke; }
.plot-max {
  position: absolute; top: 0; right: 0; font-size: 0.625rem; line-height: 1; color: var(--secondary-text-color);
  font-variant-numeric: tabular-nums;
}
.sparkline-line {
  fill: none; stroke: var(--primary-color); stroke-width: 1.5; stroke-linejoin: round; stroke-linecap: round;
  vector-effect: non-scaling-stroke;
}
.sparkline-area { fill: color-mix(in srgb, var(--primary-color) 18%, transparent); stroke: none; }

.tokens {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px; box-sizing: border-box; min-height: 48px;
  padding: 6px 12px; cursor: text;
  background: var(--input-fill-color, var(--secondary-background-color));
  border-bottom: 1px solid var(--input-idle-line-color, var(--secondary-text-color));
  border-radius: 4px 4px 0 0;
}
.tokens:focus-within { border-bottom: 2px solid var(--primary-color); }
.tokens input {
  flex: 1; min-width: 80px; height: 32px; padding: 0; border: none; outline: none; background: none;
  font: inherit; color: var(--primary-text-color);
}

.chip {
  display: inline-flex; align-items: center; max-width: 100%; height: 32px; box-sizing: border-box;
  border-radius: 16px; border: 1px solid var(--divider-color); background: var(--card-background-color);
}
.chip-body {
  display: inline-flex; align-items: center; gap: 6px; min-width: 0; padding: 0 4px 0 3px;
  border: none; background: none; font: inherit; color: inherit;
}
.chip.constant .chip-body { cursor: pointer; }
.chip-remove {
  display: inline-flex; align-items: center; justify-content: center; flex: none;
  width: 24px; height: 24px; margin-right: 4px; padding: 0; border: none; border-radius: 50%;
  background: none; color: var(--secondary-text-color); cursor: pointer;
}
.chip-remove .icon { width: 16px; height: 16px; }
.chip-remove:hover { background: var(--secondary-background-color); }

.entity-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.option .entity-name { flex: 1; }
.entity-id { font-size: 0.75rem; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; }

.options { display: flex; flex-direction: column; gap: 8px; }
.option-group {
  list-style: none; margin: 0; padding: 4px 0;
  background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 8px;
}
.option-group.entities { max-height: 280px; overflow-y: auto; }
.option { display: flex; align-items: center; gap: 12px; padding: 6px 12px; cursor: pointer; }
.option.active, .option:hover { background: var(--secondary-background-color); }
.option[aria-disabled="true"] { opacity: 0.4; cursor: default; }
.option.all {
  position: sticky; top: -4px; z-index: 1; margin-top: -4px; padding-top: 10px;
  border-bottom: 1px solid var(--divider-color); color: var(--primary-color); font-weight: 500;
  background: var(--card-background-color);
}
.option.all:hover { background: var(--secondary-background-color); }
.option-text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.buses { display: flex; flex-wrap: wrap; gap: 8px; }
.bus {
  flex: 1 1 200px; display: flex; flex-direction: column; align-items: flex-start; gap: 8px;
  padding: 10px 12px; border-radius: 12px; text-align: left; font: inherit; color: inherit; cursor: pointer;
  border: 1px solid var(--divider-color); background: var(--card-background-color);
}
.bus:hover { border-color: var(--secondary-text-color); }
.bus.selected { border: 2px solid var(--primary-color); padding: 9px 11px; }
.bus-head { display: flex; align-items: center; gap: 8px; font-weight: 500; }
.bus-head .icon { color: var(--secondary-text-color); }
.bus-icon { width: 20px; text-align: center; }
.bus.selected .bus-head .icon { color: var(--primary-color); }
.bus-elements { display: flex; flex-wrap: wrap; gap: 4px; min-height: 24px; }
.bus-element {
  display: inline-flex; align-items: center; gap: 4px; height: 24px; padding: 0 8px; border-radius: 12px;
  font-size: 0.8rem; background: var(--secondary-background-color); color: var(--secondary-text-color);
}
.bus-element.ghost {
  background: none; border: 1px dashed var(--primary-color); color: var(--primary-color);
}

.path { display: flex; flex-direction: column; align-items: stretch; }
.path-endpoint {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 12px;
  border: 1px solid var(--divider-color); background: var(--card-background-color);
}
.path-endpoint-icon { width: 20px; text-align: center; }
.path-endpoint select {
  flex: 1; min-width: 0; height: 32px; border: none; background: none; font: inherit; font-weight: 500;
  color: var(--primary-text-color);
}
.path-step { display: flex; flex-direction: column; align-items: stretch; }
.path-link { display: flex; flex-direction: column; align-items: center; padding: 0 0 0 22px; align-self: flex-start; }
.path-line { width: 2px; height: 10px; background: var(--divider-color); }
.path-arrow { position: relative; }
.path-arrow::after {
  content: ""; position: absolute; left: -4px; bottom: -4px; border: 5px solid transparent;
  border-top-color: var(--divider-color);
}
.path-add, .path-control {
  display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; padding: 0;
  border-radius: 50%; border: 1px solid var(--divider-color); background: var(--card-background-color);
  color: var(--secondary-text-color); cursor: pointer;
}
.path-control { border: none; background: none; }
.path-add:hover, .path-control:hover:not(:disabled) { background: var(--secondary-background-color); }
.path-control:disabled { opacity: 0.3; cursor: default; }
.path-kinds { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 4px 0; }
.path-kind {
  display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 12px; border-radius: 16px;
  border: 1px solid var(--primary-color); background: none; color: var(--primary-color); font: inherit; cursor: pointer;
}
.path-kind .icon { color: var(--primary-color); }
.path-segment {
  display: flex; flex-direction: column; gap: 4px; padding: 6px 12px 10px; border-radius: 12px;
  border: 1px solid var(--divider-color); background: var(--card-background-color);
}
.path-segment-head { display: flex; align-items: center; gap: 8px; color: var(--secondary-text-color); }
.path-segment-name { flex: 1; font-size: 0.875rem; }
.path-controls { display: flex; gap: 2px; }
.visually-hidden {
  position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap;
}

.rule {
  display: flex; flex-direction: column; gap: 8px; padding: 8px 12px 10px; margin-bottom: 8px; border-radius: 12px;
  border: 1px solid var(--divider-color); background: var(--card-background-color);
}
.rule-head { display: flex; align-items: center; gap: 8px; }
.rule-name {
  flex: 1; min-width: 0; height: 32px; padding: 0 8px; border: none; border-radius: 4px; font: inherit; font-weight: 500;
  background: none; color: var(--primary-text-color);
}
.rule-name:hover, .rule-name:focus { background: var(--input-fill-color, var(--secondary-background-color)); outline: none; }
.rule-switch {
  position: relative; flex: none; width: 36px; height: 20px; padding: 0; border: none; border-radius: 10px; cursor: pointer;
  background: var(--divider-color);
}
.rule-switch::after {
  content: ""; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%;
  background: var(--card-background-color); transition: left 0.15s;
}
.rule-switch.on { background: var(--primary-color); }
.rule-switch.on::after { left: 18px; }
.rule-owner { gap: 4px; }
.rule-ends { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.rule-end { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
.rule-end-label { font-size: 0.75rem; color: var(--secondary-text-color); margin-right: 2px; }
.rule-any { font-style: italic; }
.rule-arrow .icon { color: var(--secondary-text-color); }
.rule-add-end {
  width: 36px; height: 28px; padding: 0 6px; appearance: none; text-align: center; border-radius: 14px; border: 1px dashed var(--divider-color); background: none;
  font: inherit; color: var(--secondary-text-color); cursor: pointer;
}
.rule-add { align-self: flex-start; }

.buffer-preview svg { display: block; width: 100%; height: 110px; overflow: visible; }
.buffer-zone { fill: color-mix(in srgb, var(--warning-color, #ff9800) 10%, transparent); stroke: none; }
.buffer-line { fill: none; stroke: var(--warning-color, #ff9800); stroke-width: 1.5; stroke-dasharray: 4 3; vector-effect: non-scaling-stroke; }
.buffer-now { fill: none; stroke: var(--secondary-text-color); stroke-width: 1; vector-effect: non-scaling-stroke; }
.buffer-plan { fill: none; stroke: var(--primary-color); stroke-width: 2; vector-effect: non-scaling-stroke; }
.buffer-legend { display: flex; flex-wrap: wrap; gap: 12px; font-size: 0.75rem; color: var(--secondary-text-color); }
.buffer-legend span { display: inline-flex; align-items: center; gap: 4px; }
.swatch { display: inline-block; width: 14px; height: 0; border-top: 2px solid; }
.swatch.buffer-plan { border-color: var(--primary-color); }
.swatch.buffer-now { border-color: var(--secondary-text-color); border-top-width: 1px; }
.swatch.buffer-line { border-top-style: dashed; border-color: var(--warning-color, #ff9800); }
`;
