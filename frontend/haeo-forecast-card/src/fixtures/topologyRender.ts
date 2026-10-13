import { expect, vi } from "vitest";

// Rendering the topology means loading the controller chunk and running an ELK layout,
// which is slow enough that a fixed sleep races it: measured at 600-700 ms under
// full-suite parallel load, against sleeps of 500 ms. Wait for the outcome instead. The
// timeout is generous because it is only reached when the test is genuinely failing.
const RENDER_TIMEOUT_MS = 10_000;
const RENDER_POLL_MS = 25;

export async function waitForTopologySvg(host: HTMLElement): Promise<void> {
  await vi.waitFor(
    () => {
      expect(host.shadowRoot?.querySelector("svg")).toBeTruthy();
    },
    { timeout: RENDER_TIMEOUT_MS, interval: RENDER_POLL_MS }
  );
}

export async function waitForShadowText(host: HTMLElement, text: string): Promise<void> {
  await vi.waitFor(
    () => {
      expect(host.shadowRoot?.textContent).toContain(text);
    },
    { timeout: RENDER_TIMEOUT_MS, interval: RENDER_POLL_MS }
  );
}

/**
 * Wait for the initial layout to finish dispatching, and report how many `ll-update`
 * events it produced.
 *
 * The svg landing in the DOM is not the last thing to happen: `onLayoutSize` fires from
 * an effect that runs after that commit, so a count read the moment the svg appears can
 * still be one short. Wait until the count stops moving.
 */
export async function waitForSettledUpdates(host: HTMLElement, updates: Event[]): Promise<number> {
  await waitForTopologySvg(host);
  let previous = -1;
  await vi.waitFor(
    () => {
      const seen = updates.length;
      const settled = seen === previous;
      previous = seen;
      expect(settled).toBe(true);
    },
    { timeout: RENDER_TIMEOUT_MS, interval: RENDER_POLL_MS }
  );
  return updates.length;
}
