import { render } from "preact";
import { act as actAsync } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BufferPreviewField } from "./BufferPreviewField";
import type { BufferPreviewResult } from "./BufferPreviewField";
import { formData } from "./buffer-preview-selector";
import type { SelectorHass } from "./types";

const HOUR = 3600;
const RESULT: BufferPreviewResult = {
  times: [0, HOUR, 2 * HOUR],
  kind: "reserve",
  buffer: [0.2, 0.2, 0],
  plan: [0.5, 0.2, 0.2],
  current: [0.5, 0, 0],
  days: [HOUR],
};

let container: HTMLElement;
let form: Record<string, unknown>;

beforeEach(() => {
  vi.useFakeTimers();
  container = document.createElement("div");
  document.body.append(container);
  form = { name: "Outage", participants: { storage: ["Battery"] } };
});

afterEach(() => {
  render(null, container);
  container.remove();
  vi.useRealTimers();
});

async function settle(): Promise<void> {
  await actAsync(async () => {
    await vi.advanceTimersByTimeAsync(500);
  });
}

async function show(callWS: SelectorHass["callWS"]): Promise<void> {
  const hass: SelectorHass = { states: {}, localize: () => "", language: "en", ...(callWS ? { callWS } : {}) };
  await actAsync(() => {
    render(
      <BufferPreviewField hass={hass} entryId="hub" replaces={null} readForm={() => form} t={(key) => key} />,
      container
    );
  });
  await settle();
}

describe("BufferPreviewField", () => {
  it("plans with the form's values and charts the buffer, the plan with it, and the plan now", async () => {
    const callWS = vi.fn().mockResolvedValue(RESULT);
    await show(callWS as SelectorHass["callWS"]);

    expect(callWS).toHaveBeenCalledWith({ type: "haeo/buffer_preview", entry_id: "hub", replaces: null, buffer: form });
    expect(container.querySelector(".buffer-zone")).not.toBeNull();
    expect(container.querySelector(".buffer-line")?.getAttribute("points")).toBe("0.0,85.6 150.0,85.6 300.0,106.0");
    expect(container.querySelector(".buffer-plan")).not.toBeNull();
    expect(container.querySelector(".buffer-now")).not.toBeNull();
    expect(container.querySelectorAll(".plot-day")).toHaveLength(1);
  });

  it("plans again once the form settles after a field changes, but not when nothing changed", async () => {
    const callWS = vi.fn().mockResolvedValue(RESULT);
    await show(callWS as SelectorHass["callWS"]);

    document.dispatchEvent(new CustomEvent("value-changed"));
    await settle();
    form = { ...form, kind: "headroom" };
    document.dispatchEvent(new CustomEvent("value-changed"));
    document.dispatchEvent(new CustomEvent("value-changed"));
    await settle();

    expect(callWS).toHaveBeenCalledTimes(2);
    expect(callWS).toHaveBeenLastCalledWith(expect.objectContaining({ buffer: form }));
  });

  it("shows nothing while the buffer cannot be planned", async () => {
    await show(vi.fn().mockRejectedValue(new Error("needs a battery")) as SelectorHass["callWS"]);

    expect(container.querySelector("svg")).toBeNull();
  });
});

describe("formData", () => {
  it("reads the outermost form around an element, through shadow roots", () => {
    const outer = Object.assign(document.createElement("ha-form"), { data: { name: "Outage" } });
    const inner = Object.assign(document.createElement("ha-form"), { data: { window: 12 } });
    const field = document.createElement("div");
    outer.attachShadow({ mode: "open" }).append(inner);
    inner.attachShadow({ mode: "open" }).append(field);

    expect(formData(field)).toEqual({ name: "Outage" });
    expect(formData(document.createElement("div"))).toBeNull();
  });
});
