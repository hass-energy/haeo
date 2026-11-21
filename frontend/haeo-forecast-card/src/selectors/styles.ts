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
.icon { width: 20px; height: 20px; fill: currentColor; flex: none; }
.row { display: flex; align-items: center; gap: 4px; }
.row:empty { display: none; }

.number, .search {
  display: flex; align-items: center; gap: 8px; box-sizing: border-box; height: 40px; padding: 0 12px;
  background: var(--input-fill-color, var(--secondary-background-color));
  border-bottom: 1px solid var(--input-idle-line-color, var(--secondary-text-color));
  border-radius: 4px 4px 0 0;
}
.number:focus-within, .search:focus-within { border-bottom: 2px solid var(--primary-color); }
.number { width: 180px; }
.search { color: var(--secondary-text-color); }
.search.inline { flex: 1; }
input[type="number"], input[type="text"] {
  flex: 1; min-width: 0; height: 100%; padding: 0; border: none; outline: none; background: none;
  font: inherit; color: var(--primary-text-color);
}
.unit { color: var(--secondary-text-color); }

.entities { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.entity {
  display: flex; align-items: center; gap: 12px; padding: 4px 4px 4px 12px;
  border: 1px solid var(--divider-color); border-radius: 8px;
}
.entity-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.entity-id { font-size: 0.75rem; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; }
.entity-state { color: var(--secondary-text-color); white-space: nowrap; font-variant-numeric: tabular-nums; }

button { font: inherit; cursor: pointer; }
.icon-button {
  display: inline-flex; align-items: center; justify-content: center; flex: none;
  width: 36px; height: 36px; padding: 0; border: none; border-radius: 50%;
  background: none; color: var(--secondary-text-color);
}
.icon-button:hover, .icon-button.active { background: var(--secondary-background-color); color: var(--primary-color); }

.switch {
  position: relative; width: 40px; height: 22px; padding: 0; border: none; border-radius: 11px;
  background: var(--switch-unchecked-track-color, var(--disabled-color, #bdbdbd));
}
.switch .knob {
  position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%;
  background: var(--switch-unchecked-button-color, #fff); transition: left 0.15s;
}
.switch[aria-checked="true"] { background: var(--switch-checked-track-color, var(--primary-color)); }
.switch[aria-checked="true"] .knob { left: 21px; background: var(--switch-checked-button-color, #fff); }
.switch.unset { opacity: 0.5; }

.picker {
  display: flex; flex-direction: column; border: 1px solid var(--divider-color); border-radius: 8px;
  background: var(--card-background-color); overflow: hidden;
}
.picker .search { border-radius: 0; }
.options { list-style: none; margin: 0; padding: 4px 0; max-height: 280px; overflow-y: auto; }
.option { display: flex; align-items: center; gap: 12px; padding: 6px 12px; cursor: pointer; }
.option:hover { background: var(--secondary-background-color); }
.option.all { border-bottom: 1px solid var(--divider-color); }
.option input[type="checkbox"] { margin: 0; accent-color: var(--primary-color); pointer-events: none; }
.option-text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.count { color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
`;
