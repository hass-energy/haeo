import { afterEach, describe, expect, it } from "vitest";

import { dispatchLovelaceUpdate } from "./lovelace-events";

describe("dispatchLovelaceUpdate", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("dispatches ll-update using the host document Event constructor", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);

    const updates: Event[] = [];
    host.addEventListener("ll-update", (event: Event) => {
      updates.push(event);
    });

    dispatchLovelaceUpdate(host);

    expect(updates).toHaveLength(1);
    expect(updates[0]?.type).toBe("ll-update");
    expect(updates[0]?.bubbles).toBe(true);
  });
});
