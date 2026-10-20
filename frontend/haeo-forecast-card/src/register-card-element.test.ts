import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * A registry standing in for the scoped custom element registry polyfill that Home
 * Assistant installs over `window.customElements`, which starts with none of the
 * registrations made against the registry it replaces.
 */
function freshRegistry(): Pick<CustomElementRegistry, "define" | "get"> {
  const definitions = new Map<string, CustomElementConstructor>();
  return {
    define(name: string, ctor: CustomElementConstructor): void {
      if (definitions.has(name)) {
        throw new DOMException(`${name} has already been defined`, "NotSupportedError");
      }
      definitions.set(name, ctor);
    },
    get(name: string): CustomElementConstructor | undefined {
      return definitions.get(name);
    },
  };
}

const cards: [string, () => Promise<unknown>][] = [
  ["haeo-forecast-card", () => import("./card")],
  ["haeo-topology-card", () => import("./topology-card")],
];

describe("card element registration", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it.each(cards)("re-registers %s after the registry is swapped", async (tag, load) => {
    await load();
    const ctor = customElements.get(tag);
    expect(ctor).toBeDefined();

    const swapped = freshRegistry();
    vi.stubGlobal("customElements", swapped);
    vi.advanceTimersByTime(1000);

    expect(swapped.get(tag)).toBe(ctor);
  });

  it("stops re-registering once the swap window has passed, even with the clock pinned", async () => {
    // Leave Date alone so the clock does not move with the timers, as in the scenario exporters
    vi.useRealTimers();
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    const { registerCardElement } = await import("./register-card-element");
    class LateCard extends HTMLElement {}
    registerCardElement("haeo-late-card", LateCard);

    vi.advanceTimersByTime(11_000);
    const swapped = freshRegistry();
    vi.stubGlobal("customElements", swapped);
    vi.advanceTimersByTime(11_000);

    expect(swapped.get("haeo-late-card")).toBeUndefined();
  });
});
