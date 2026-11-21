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
.empty { color: var(--secondary-text-color); font-style: italic; }
.entities { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.entity {
  display: flex; align-items: center; gap: 12px; padding: 6px 6px 6px 12px;
  border: 1px solid var(--divider-color); border-radius: 8px;
}
.entity-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.entity-id { font-size: 0.75rem; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; }
.entity-state { color: var(--secondary-text-color); white-space: nowrap; font-variant-numeric: tabular-nums; }
.constant { display: flex; align-items: center; gap: 8px; }
.unit { color: var(--secondary-text-color); }
input {
  box-sizing: border-box; height: 40px; padding: 0 12px; font: inherit; color: inherit;
  background: var(--input-fill-color, var(--secondary-background-color));
  border: none; border-bottom: 1px solid var(--input-idle-line-color, var(--secondary-text-color));
  border-radius: 4px 4px 0 0; outline: none;
}
input:focus { border-bottom: 2px solid var(--primary-color); }
.constant input { width: 160px; }
.search input { width: 100%; }
.options {
  list-style: none; margin: 4px 0 0; padding: 4px 0; max-height: 280px; overflow-y: auto;
  background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 8px;
}
.option { display: flex; align-items: center; gap: 8px; padding: 6px 12px; cursor: pointer; }
.option.active, .option:hover { background: var(--secondary-background-color); }
.option.action { color: var(--primary-color); }
.option-text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.check { width: 1em; color: var(--primary-color); }
.hint { margin-top: 4px; font-size: 0.8rem; color: var(--secondary-text-color); }
.no-matches { padding: 6px 12px; color: var(--secondary-text-color); }
button { font: inherit; cursor: pointer; }
.icon-button {
  border: none; background: none; color: var(--secondary-text-color);
  width: 28px; height: 28px; border-radius: 50%; font-size: 1.1rem;
}
.icon-button:hover { background: var(--secondary-background-color); }
.text-button { align-self: flex-start; border: none; background: none; color: var(--primary-color); padding: 2px 0; }
.switch {
  min-width: 64px; height: 32px; border-radius: 16px; border: 1px solid var(--divider-color);
  background: var(--secondary-background-color); color: var(--primary-text-color);
}
.switch[aria-checked="true"] { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
`;
