/**
 * Register a card's custom element, and keep it registered while the page settles.
 *
 * Home Assistant can replace `window.customElements` with the scoped custom element
 * registry polyfill after a card bundle has already run. The replacement registry does
 * not carry over registrations made against the native one, so an element that
 * registered without error silently disappears and Lovelace renders "Custom element
 * doesn't exist". Whether the bundle or the polyfill runs first depends on cache state
 * and load order, which makes the failure intermittent.
 *
 * Registering once is not enough, and neither is retrying until the first success,
 * since that success can land in the registry about to be discarded. The element is
 * therefore re-registered whenever it goes missing, for long enough to cover the swap.
 */

// Counted in ticks rather than against the clock, so the retries still end when the
// clock is pinned, as it is when the scenario exporters render a card.
const RETRY_INTERVAL_MS = 50;
const RETRY_TICKS = 200;

const activeRetries = new Set<ReturnType<typeof setInterval>>();

export function registerCardElement(tag: string, ctor: CustomElementConstructor): void {
  const ensure = (): void => {
    if (customElements.get(tag) === undefined) {
      customElements.define(tag, ctor);
    }
  };

  ensure();

  let ticks = 0;
  const timer = setInterval(() => {
    ensure();
    ticks += 1;
    if (ticks >= RETRY_TICKS) {
      clearInterval(timer);
      activeRetries.delete(timer);
    }
  }, RETRY_INTERVAL_MS);
  activeRetries.add(timer);
}

/**
 * Cancel any retries still running.
 *
 * Production never needs this, since the retries end on their own. Tests do, so an
 * interval started by loading a card module cannot outlive the test environment.
 */
export function stopCardElementRetries(): void {
  for (const timer of activeRetries) {
    clearInterval(timer);
  }
  activeRetries.clear();
}
