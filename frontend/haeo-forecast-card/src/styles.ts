export const CARD_STYLES = `
  :host,
  .haeoThemeRoot,
  [data-theme] {
    display: block;
    position: relative;
    --haeo-bg: var(--card-background-color, #ffffff);
    --haeo-divider: var(--divider-color, #d9dde6);
    --haeo-text: var(--primary-text-color, #18202a);
    --haeo-subtext: var(--secondary-text-color, #5d6878);
    --haeo-accent: var(--primary-color, #1c63e9);
    --haeo-load-0: #1f2937;
    --haeo-load-1: #111827;
    --haeo-load-2: #374151;
    --haeo-load-3: #4b5563;
    font-family:
      "Segoe UI",
      "Roboto",
      system-ui,
      sans-serif;
    color: var(--haeo-text);
  }

  @media (prefers-color-scheme: dark) {
    :host,
    .haeoThemeRoot,
    [data-theme] {
      --haeo-bg: var(--card-background-color, #1f232b);
      --haeo-divider: var(--divider-color, #414a59);
      --haeo-text: var(--primary-text-color, #e3e8ef);
      --haeo-subtext: var(--secondary-text-color, #a8b1c0);
      --haeo-accent: var(--primary-color, #8ab4ff);
      --haeo-load-0: #f9fafb;
      --haeo-load-1: #e5e7eb;
      --haeo-load-2: #d1d5db;
      --haeo-load-3: #9ca3af;
    }
  }

  ha-card {
    overflow: hidden;
    position: relative;
    min-height: 220px;
    background: var(--haeo-bg);
    color: var(--haeo-text);
  }

  .title {
    font-size: 1rem;
    font-weight: 600;
    padding: 16px 16px 0;
    color: var(--haeo-text);
  }

  svg {
    width: 100%;
    display: block;
    touch-action: none;
  }

  .axisLabel {
    fill: var(--haeo-subtext);
    font-size: 11px;
    dominant-baseline: middle;
  }

  .axisLabelStrong {
    fill: var(--haeo-subtext);
    font-size: 11px;
    font-weight: 600;
  }

  .axisTickLabel {
    fill: var(--haeo-subtext);
    font-size: 10px;
  }

  .laneDivider {
    stroke: color-mix(in oklab, var(--haeo-divider) 70%, transparent);
    stroke-width: 1;
  }

  .gridMajor {
    stroke: color-mix(in oklab, var(--haeo-divider) 50%, transparent);
    stroke-width: 1;
    stroke-dasharray: 3 4;
  }

  .gridMinor {
    stroke: color-mix(in oklab, var(--haeo-divider) 32%, transparent);
    stroke-width: 0.8;
    stroke-dasharray: 1 4;
  }

  .axisBase {
    stroke: color-mix(in oklab, var(--haeo-text) 60%, transparent);
    stroke-width: 1.2;
  }

  .axisZero {
    stroke: color-mix(in oklab, var(--haeo-accent) 50%, var(--haeo-divider));
    stroke-width: 1.4;
  }

  .hoverLine {
    stroke: var(--haeo-accent);
    stroke-width: 1;
    stroke-dasharray: 4 4;
    pointer-events: none;
  }

  .lineSeries {
    fill: none;
    stroke-width: 2.2;
    pointer-events: none;
  }

  .priceLine {
    stroke-width: 2.4;
  }

  .socLine {
    stroke-width: 1.8;
    stroke-dasharray: 6 4;
  }

  .areaSeries {
    stroke-width: 1;
    pointer-events: none;
    transition:
      opacity 90ms linear,
      stroke-width 90ms linear;
  }

  .areaSeries.active {
    stroke-width: 2;
  }

  .legendWrap {
    padding: 0 16px 14px;
  }

  .legendControls {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
  }

  .legendModeToggle {
    appearance: none;
    border: 1px solid color-mix(in oklab, var(--haeo-divider) 70%, transparent);
    background: color-mix(in oklab, var(--haeo-bg) 90%, #000 10%);
    color: var(--haeo-text);
    font: inherit;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 11px;
    line-height: 1.2;
    cursor: pointer;
  }

  .legend {
    display: grid;
    gap: 6px;
    font-size: 12px;
  }

  .legendElement {
    display: grid;
    gap: 6px;
    border: 1px solid color-mix(in oklab, var(--haeo-divider) 62%, transparent);
    border-radius: 999px;
    padding: 4px 8px;
    background: color-mix(in oklab, var(--haeo-bg) 94%, #000 6%);
    transition: opacity 120ms ease-out;
  }

  .legendElement.active {
    opacity: 1;
  }

  .legendElement.dimmed {
    opacity: 0.4;
  }

  .legendElement.disabled {
    opacity: 0.45;
  }

  .legendElementLabel {
    appearance: none;
    border: none;
    background: transparent;
    padding: 0;
    color: var(--haeo-text);
    font: inherit;
    cursor: pointer;
    text-align: left;
  }

  .legendGroupTitle {
    font-size: 11px;
    font-weight: 650;
    color: var(--haeo-text);
    margin: 0;
  }

  .legendIconRow {
    display: flex;
    flex-wrap: nowrap;
    gap: 4px;
    align-items: center;
  }

  .legendItem {
    appearance: none;
    border: 1px solid color-mix(in oklab, currentColor 50%, transparent);
    background: color-mix(in oklab, var(--haeo-bg) 93%, #000 7%);
    border-radius: 999px;
    padding: 3px 6px;
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    cursor: pointer;
    color: var(--haeo-text);
    font: inherit;
    opacity: 0.72;
    width: 24px;
    height: 24px;
    justify-content: center;
  }

  .legendItem.active {
    opacity: 1;
    box-shadow: 0 0 0 1px color-mix(in oklab, currentColor 60%, transparent);
  }

  .legendItem.disabled {
    opacity: 0.3;
  }

  .legendIcon {
    width: 13px;
    height: 13px;
    color: currentColor;
    fill: currentColor;
  }

  .tooltip {
    position: absolute;
    right: 14px;
    top: 14px;
    max-width: min(320px, calc(100% - 28px));
    background: color-mix(in oklab, var(--haeo-bg) 86%, #000 14%);
    border: 1px solid color-mix(in oklab, var(--haeo-divider) 70%, transparent);
    border-radius: 10px;
    padding: 10px 11px;
    backdrop-filter: blur(6px);
    font-size: 12px;
    pointer-events: none;
    color: var(--haeo-text);
  }

  .tooltipTime {
    font-weight: 600;
    margin-bottom: 6px;
  }

  .tooltipRow {
    display: grid;
    grid-template-columns: 10px 1fr auto;
    align-items: center;
    gap: 6px;
    line-height: 1.35;
    margin-bottom: 3px;
    opacity: 0.74;
  }

  .tooltipRow.active {
    opacity: 1;
    font-weight: 600;
  }

  .tooltipGroup {
    margin-bottom: 6px;
  }

  .tooltipGroupTitle {
    color: var(--haeo-subtext);
    font-size: 11px;
    font-weight: 600;
    margin-bottom: 3px;
  }

  .tooltipDot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
  }

  .tooltipTotals {
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid color-mix(in oklab, var(--haeo-divider) 70%, transparent);
    display: grid;
    gap: 3px;
  }

  .empty {
    padding: 20px 16px 18px;
    color: var(--haeo-subtext);
    font-size: 0.9rem;
  }
`;
