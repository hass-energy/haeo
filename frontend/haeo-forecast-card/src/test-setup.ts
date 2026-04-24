/**
 * jsdom polyfills for browser APIs missing from the test environment.
 *
 * jsdom does not implement several browser APIs that HAEO's forecast card
 * relies on. Rather than scattering try/catch guards and feature-detection
 * throughout source code, we polyfill them here so the card code can use
 * standard browser APIs without test-environment workarounds.
 *
 * Loaded via vitest.config.ts `setupFiles` for all tests using the jsdom
 * environment.
 */

/* eslint-disable @typescript-eslint/no-empty-function */

// --- matchMedia ---
// jsdom does not implement window.matchMedia. The card queries
// prefers-reduced-motion to decide animation behavior.
if (typeof globalThis.matchMedia !== "function") {
  globalThis.matchMedia = (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
    addListener: () => {},
    removeListener: () => {},
  });
}

// --- ResizeObserver ---
// jsdom does not implement ResizeObserver. The card uses it to track
// container width for responsive sizing.
if (typeof globalThis.ResizeObserver !== "function") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  };
}

// --- IntersectionObserver ---
// jsdom does not implement IntersectionObserver. The card uses it to
// pause animation when the element is scrolled off-screen.
if (typeof globalThis.IntersectionObserver !== "function") {
  globalThis.IntersectionObserver = class IntersectionObserver {
    readonly root: Element | null = null;
    readonly rootMargin: string = "0px";
    readonly thresholds: ReadonlyArray<number> = [0];
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
  };
}

// --- SVGSVGElement.getScreenCTM ---
// jsdom does not implement getScreenCTM on SVG elements. The card uses
// it to convert pointer coordinates from screen space to SVG space.
const origCreateElement = document.createElementNS.bind(document);
document.createElementNS = function (ns: string | null, tag: string) {
  const el = origCreateElement(ns, tag);
  if (ns === "http://www.w3.org/2000/svg" && tag === "svg" && !("getScreenCTM" in el)) {
    const identity = {
      a: 1,
      b: 0,
      c: 0,
      d: 1,
      e: 0,
      f: 0,
      inverse() {
        return this;
      },
    };
    Object.defineProperty(el, "getScreenCTM", {
      value: () => identity,
      configurable: true,
    });
  }
  return el;
} as typeof document.createElementNS;
