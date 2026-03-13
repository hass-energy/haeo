export const CARD_STYLES = `
  :host {
    display: block;
    position: relative;
    font-family:
      "Segoe UI",
      "Roboto",
      system-ui,
      sans-serif;
  }

  ha-card {
    overflow: hidden;
    position: relative;
    min-height: 220px;
  }

  .title {
    font-size: 1rem;
    font-weight: 600;
    padding: 16px 16px 0;
  }

  svg {
    width: 100%;
    display: block;
    touch-action: none;
  }

  .axisLabel {
    fill: var(--secondary-text-color);
    font-size: 11px;
    dominant-baseline: middle;
  }

  .axisLabelStrong {
    fill: var(--secondary-text-color);
    font-size: 11px;
    font-weight: 600;
  }

  .axisTickLabel {
    fill: var(--secondary-text-color);
    font-size: 10px;
    dominant-baseline: middle;
  }

  .laneDivider {
    stroke: color-mix(in oklab, var(--divider-color) 70%, transparent);
    stroke-width: 1;
  }

  .gridMajor {
    stroke: color-mix(in oklab, var(--divider-color) 50%, transparent);
    stroke-width: 1;
    stroke-dasharray: 3 4;
  }

  .gridMinor {
    stroke: color-mix(in oklab, var(--divider-color) 32%, transparent);
    stroke-width: 0.8;
    stroke-dasharray: 1 4;
  }

  .hoverLine {
    stroke: var(--primary-color);
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
  }

  .legend {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 6px 10px;
    padding: 0 16px 14px;
    font-size: 12px;
  }

  .legendItem {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    cursor: pointer;
    color: var(--primary-text-color);
    opacity: 0.72;
  }

  .legendItem.active {
    opacity: 1;
    font-weight: 600;
  }

  .legendSwatch {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    flex: 0 0 auto;
  }

  .legendText {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tooltip {
    position: absolute;
    right: 14px;
    top: 14px;
    max-width: min(320px, calc(100% - 28px));
    background: color-mix(in oklab, var(--card-background-color) 86%, #000 14%);
    border: 1px solid color-mix(in oklab, var(--divider-color) 70%, transparent);
    border-radius: 10px;
    padding: 10px 11px;
    backdrop-filter: blur(6px);
    font-size: 12px;
    pointer-events: none;
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
  }

  .tooltipDot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
  }

  .tooltipTotals {
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid color-mix(in oklab, var(--divider-color) 70%, transparent);
    display: grid;
    gap: 3px;
  }

  .empty {
    padding: 20px 16px 18px;
    color: var(--secondary-text-color);
    font-size: 0.9rem;
  }
`;
