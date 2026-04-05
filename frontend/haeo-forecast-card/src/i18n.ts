type TranslationValue = string;

type TranslationDict = Record<string, TranslationValue>;

const EN_TRANSLATIONS: TranslationDict = {
  "card.title.default": "HAEO forecast",
  "card.empty.message":
    "No forecast data found. Add forecast entities in card config or ensure HAEO output sensors are available.",
  "axis.power": "Power (kW)",
  "axis.price": "Price",
  "axis.soc": "SOC",
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
  "tooltip.total.produced": "Produced supply",
  "tooltip.total.available": "Available supply",
  "tooltip.total.consumed": "Active load",
  "tooltip.total.possible": "Possible load",
  "tooltip.total.generic": "{lane} total",
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
  "editor.hub.label": "HAEO hub entry",
  "editor.hub.none": "No HAEO hubs with forecast entities found",
  "editor.discovery.loading": "Discovering HAEO hubs and forecast entities...",
  "editor.discovery.count": "Discovered entities for selected hub: {count}",
  "editor.elements.label": "Elements: {elements}",
  "editor.height.label": "Chart height (optional)",
  "editor.height.placeholder": "auto",
};

const TRANSLATIONS: Record<string, TranslationDict> = {
  en: EN_TRANSLATIONS,
};

function normalizeLocale(locale: string | null | undefined): string {
  if (!locale) {
    return "en";
  }
  const normalized = locale.toLowerCase().replace("_", "-");
  if (TRANSLATIONS[normalized]) {
    return normalized;
  }
  const base = normalized.split("-")[0];
  return base && TRANSLATIONS[base] ? base : "en";
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
