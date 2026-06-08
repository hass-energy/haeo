import { render } from "preact";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TopologyCardView } from "./TopologyCardView";
import * as topologyCardUtils from "../topology-card-utils";
import type { HassLike } from "../series";

describe("TopologyCardView", () => {
  const root = document.createElement("div");

  afterEach(() => {
    render(null, root);
    vi.restoreAllMocks();
  });

  it("shows the hub-not-found message when the configured hub no longer exists", () => {
    const hass: HassLike = {
      states: {},
      entities: {},
      devices: {},
    };

    render(
      <TopologyCardView
        config={{ type: "custom:haeo-topology-card", hub_entry_id: "hub-alpha" }}
        hass={hass}
        locale="en"
        onLayoutHeight={() => undefined}
      />,
      root
    );

    expect(root.textContent).toContain("The selected HAEO hub no longer exists");
  });

  it("shows the no-entity message when a hub is selected but topology cannot be resolved", () => {
    const hass: HassLike = {
      states: {},
      entities: {},
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    render(
      <TopologyCardView
        config={{ type: "custom:haeo-topology-card", hub_entry_id: "hub-alpha" }}
        hass={hass}
        locale="en"
        onLayoutHeight={() => undefined}
      />,
      root
    );

    expect(root.textContent).toContain("No optimization status sensor found for the selected hub");
  });

  it("shows the waiting message when topology data is not available yet", () => {
    vi.spyOn(topologyCardUtils, "resolveTopology").mockReturnValue({
      status: "waiting",
      entityId: "sensor.haeo_status",
    });

    render(
      <TopologyCardView
        config={{ type: "custom:haeo-topology-card", hub_entry_id: "hub-alpha" }}
        hass={{ states: {} }}
        locale="en"
        onLayoutHeight={() => undefined}
      />,
      root
    );

    expect(root.textContent).toContain("Waiting for topology data on sensor.haeo_status");
  });
});
