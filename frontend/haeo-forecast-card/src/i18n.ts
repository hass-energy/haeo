type TranslationValue = string;

type TranslationDict = Record<string, TranslationValue>;

const EN_TRANSLATIONS: TranslationDict = {
  "card.title.default": "HAEO forecast",
  "card.empty.message":
    "No forecast data found. Add forecast entities in card config or ensure HAEO output sensors are available.",
  "header.horizon": "Horizon: {hours}",
  "axis.power": "Power (kW)",
  "axis.price": "Price",
  "legend.mode": "Mode",
  "legend.mode.opposed": "Opposed",
  "legend.mode.overlay": "Overlay",
  "legend.toggle.element": "Toggle {element} series",
  "tooltip.section.produced": "Produced",
  "tooltip.section.available": "Available",
  "tooltip.section.consumed": "Consumed",
  "tooltip.section.possible": "Possible",
  "tooltip.section.price": "Price",
  "tooltip.section.soc": "State of charge",
  "tooltip.visibility.hide": "Hide hover details",
  "tooltip.visibility.show": "Show hover details",
  "legend.series.import_price": "{label} (import price)",
  "legend.series.export_price": "{label} (export price)",
  "legend.series.available": "{label} (available)",
  "legend.series.produced": "{label} (produced)",
  "legend.series.possible": "{label} (possible)",
  "legend.series.consumed": "{label} (consumed)",
  "legend.group.min": "Min",
  "legend.group.max": "Max",
  "legend.group.current": "Current",
  "legend.group.battery_bundle": "Min / max / current",
  "legend.group.battery_power": "Charge / discharge",
  "legend.group.battery_soc": "Min / max / charge %",
  "legend.group.toggle": "Toggle {element} {group}",
  "editor.error.ws_unavailable": "Home Assistant websocket API unavailable in editor.",
  "editor.title.label": "Title",
  "editor.title.placeholder": "HAEO forecast",
  "editor.discovery.loading": "Discovering HAEO hubs and forecast entities...",
  "editor.discovery.count": "Discovered entities for selected hub: {count}",
  "editor.elements.label": "Elements: {elements}",
};

const TRANSLATIONS: Record<string, TranslationDict> = {
  en: EN_TRANSLATIONS,
};

function normalizeLocale(locale: string | null | undefined): string {
  if (locale === null || locale === undefined || locale === "") {
    return "en";
  }
  const normalized = locale.toLowerCase().replace("_", "-");
  if (TRANSLATIONS[normalized] !== undefined) {
    return normalized;
  }
  const base = normalized.split("-")[0];
  return base !== undefined && TRANSLATIONS[base] !== undefined ? base : "en";
}

function interpolate(template: string, params: Record<string, string | number> | undefined): string {
  if (!params) {
    return template;
  }
  return template.replace(/\{(\w+)\}/g, (_match, key: string) => {
    const value = params[key];
    return value === undefined ? `{${key}}` : String(value);
  });
}

export function t(locale: string | null | undefined, key: string, params?: Record<string, string | number>): string {
  const resolvedLocale = normalizeLocale(locale);
  const dict = TRANSLATIONS[resolvedLocale] ?? EN_TRANSLATIONS;
  const fallback = EN_TRANSLATIONS[key] ?? key;
  const template = dict[key] ?? fallback;
  return interpolate(template, params);
}
