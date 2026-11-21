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

.tokens {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px; box-sizing: border-box; min-height: 48px;
  padding: 6px 12px; cursor: text;
  background: var(--input-fill-color, var(--secondary-background-color));
  border-bottom: 1px solid var(--input-idle-line-color, var(--secondary-text-color));
  border-radius: 4px 4px 0 0;
}
.tokens:focus-within { border-bottom: 2px solid var(--primary-color); }
.tokens > .icon { color: var(--secondary-text-color); }
.tokens input {
  flex: 1; min-width: 80px; height: 32px; padding: 0; border: none; outline: none; background: none;
  font: inherit; color: var(--primary-text-color);
}

.chip {
  display: inline-flex; align-items: center; max-width: 100%; height: 32px; box-sizing: border-box;
  border-radius: 16px; border: 1px solid var(--divider-color); background: var(--card-background-color);
}
.chip-body {
  display: inline-flex; align-items: center; gap: 6px; min-width: 0; padding: 0 4px 0 10px;
  border: none; background: none; font: inherit; color: inherit;
}
.chip.entity .icon { color: var(--secondary-text-color); }
.chip.constant {
  border-color: transparent;
  background: color-mix(in srgb, var(--primary-color) 18%, transparent);
}
.chip.constant .chip-body { cursor: pointer; font-variant-numeric: tabular-nums; }
.chip.constant .icon { color: var(--primary-color); }
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
.entity-state { color: var(--secondary-text-color); white-space: nowrap; font-variant-numeric: tabular-nums; }

.options {
  list-style: none; margin: 0; padding: 4px 0; max-height: 280px; overflow-y: auto;
  background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 8px;
}
.option { display: flex; align-items: center; gap: 12px; padding: 6px 12px; cursor: pointer; }
.option.active, .option:hover { background: var(--secondary-background-color); }
.option.constant .icon { color: var(--primary-color); }
.option.constant { font-variant-numeric: tabular-nums; }
.option[aria-disabled="true"] { opacity: 0.4; cursor: default; }
.option.all { border-bottom: 1px solid var(--divider-color); }
.option input[type="checkbox"] { margin: 0; accent-color: var(--primary-color); pointer-events: none; }
.option-text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.count { color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
`;
