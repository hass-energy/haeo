import { render } from "preact";
import { act as actAsync } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BufferPreviewField, summary } from "./BufferPreviewField";
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

  it("shows only the answer to the latest request, whichever arrives last", async () => {
    let answerFirst: (answer: BufferPreviewResult) => void = () => undefined;
    const callWS = vi
      .fn()
      .mockReturnValueOnce(new Promise<BufferPreviewResult>((resolve) => (answerFirst = resolve)))
      .mockResolvedValueOnce({ ...RESULT, kind: "headroom" });
    await show(callWS as SelectorHass["callWS"]);

    form = { ...form, kind: "headroom" };
    document.dispatchEvent(new CustomEvent("value-changed"));
    await settle();
    await actAsync(async () => {
      answerFirst(RESULT);
      await vi.advanceTimersByTimeAsync(0);
    });

    const zone = container.querySelector(".buffer-zone")?.getAttribute("points") ?? "";
    expect(zone.startsWith("0,4.0")).toBe(true);
  });

  it("plans the same form again after the hub could not plan it", async () => {
    const callWS = vi.fn().mockRejectedValueOnce(new Error("hub reloading")).mockResolvedValue(RESULT);
    await show(callWS as SelectorHass["callWS"]);

    document.dispatchEvent(new CustomEvent("value-changed"));
    await settle();

    expect(callWS).toHaveBeenCalledTimes(2);
    expect(container.querySelector("svg")).not.toBeNull();
  });

  it("shows nothing while the buffer cannot be planned", async () => {
    await show(vi.fn().mockRejectedValue(new Error("needs a battery")) as SelectorHass["callWS"]);

    expect(container.querySelector("svg")).toBeNull();
  });
});

describe("summary", () => {
  const t = (key: string, values: Record<string, string> = {}): string => `${key} ${JSON.stringify(values)}`;

  it("says how much charge a reserve keeps and how low the batteries go with it and now", () => {
    expect(summary(RESULT, t)).toBe('buffer_preview.options.summary_reserve {"held":"20","plan":"20","now":"0"}');
  });

  it("says how much space headroom keeps and how high the batteries go with it and now", () => {
    const headroom = {
      ...RESULT,
      kind: "headroom",
      buffer: [1, 0.7, 1],
      plan: [0.5, 0.7, 0.6],
      current: [0.5, 0.9, 1],
    };
    expect(summary(headroom, t)).toBe('buffer_preview.options.summary_headroom {"held":"30","plan":"70","now":"100"}');
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
