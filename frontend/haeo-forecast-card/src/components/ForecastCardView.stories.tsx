import type { Meta, StoryObj } from "@storybook/preact";
import { useLayoutEffect, useRef } from "preact/hooks";

import { STORY_SCENARIOS, getScenarioFixture } from "../fixtures/scenarioFixtures";
import type { HorizonOption } from "../store";
import type { PowerDisplayMode } from "../types";
import "../card";
import type { StoryDataMode, StoryScenario } from "../fixtures/scenarioFixtures";
import type { ForecastCardConfig } from "../types";
import type { HassLike } from "../series";

interface StoryArgs {
  powerDisplayMode: PowerDisplayMode;
  scenario: StoryScenario;
  dataMode: StoryDataMode;
}

const defaultScenario = STORY_SCENARIOS[0] ?? "scenario1";
const STORY_HORIZON_OPTIONS: HorizonOption[] = [
  15 * 60_000,
  30 * 60_000,
  60 * 60_000,
  2 * 60 * 60_000,
  4 * 60 * 60_000,
  8 * 60 * 60_000,
  12 * 60 * 60_000,
  null,
];

const meta: Meta<StoryArgs> = {
  title: "ForecastCard/ForecastCardView",
  args: {
    powerDisplayMode: "opposed",
    scenario: defaultScenario,
    dataMode: "mixed",
  },
  argTypes: {
    powerDisplayMode: {
      control: { type: "inline-radio" },
      options: ["opposed", "overlay"],
    },
    scenario: {
      control: { type: "inline-radio" },
      options: STORY_SCENARIOS,
    },
    dataMode: {
      control: { type: "inline-radio" },
      options: ["mixed", "inputs", "outputs"],
    },
  },
};

export default meta;
type Story = StoryObj<StoryArgs>;

interface StoryCardElement extends HTMLElement {
  setConfig: (config: ForecastCardConfig) => void;
  hass: HassLike | null;
}

function setShadowHorizon(element: StoryCardElement, horizon: HorizonOption): void {
  const slider = element.shadowRoot?.querySelector<HTMLInputElement>(".horizonSlider");
  if (!slider) {
    return;
  }
  slider.value = String(
    Math.max(
      0,
      STORY_HORIZON_OPTIONS.findIndex((option) => option === horizon)
    )
  );
  slider.dispatchEvent(new InputEvent("input", { bubbles: true }));
}

function dispatchInitialPointer(element: StoryCardElement, initialPointer: { x: number; y: number }): void {
  const svg = element.shadowRoot?.querySelector<SVGSVGElement>(".chartContainer > svg");
  if (!svg) {
    return;
  }
  const rect = svg.getBoundingClientRect();
  svg.dispatchEvent(
    new PointerEvent("pointermove", {
      bubbles: true,
      clientX: rect.left + initialPointer.x,
      clientY: rect.top + initialPointer.y,
    })
  );
}

function ForecastCardElementFrame(props: {
  args: StoryArgs;
  initialHorizon?: HorizonOption;
  initialPointer?: { x: number; y: number };
}): preact.JSX.Element {
  const ref = useRef<StoryCardElement>(null);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) {
      return;
    }
    element.setConfig({
      type: "custom:haeo-forecast-card",
      title: `${props.args.scenario} forecast (${props.args.dataMode})`,
      animation_mode: "off",
      power_display_mode: props.args.powerDisplayMode,
    });
    element.hass = getScenarioFixture(props.args.scenario, props.args.dataMode);

    let firstFrame = 0;
    let secondFrame = 0;
    if (props.initialPointer || props.initialHorizon !== undefined) {
      firstFrame = requestAnimationFrame(() => {
        secondFrame = requestAnimationFrame(() => {
          if (props.initialHorizon !== undefined) {
            setShadowHorizon(element, props.initialHorizon);
          }
          if (props.initialPointer) {
            dispatchInitialPointer(element, props.initialPointer);
          }
        });
      });
    }
    return () => {
      cancelAnimationFrame(firstFrame);
      cancelAnimationFrame(secondFrame);
    };
  }, [
    props.args.scenario,
    props.args.dataMode,
    props.args.powerDisplayMode,
    props.initialHorizon,
    props.initialPointer,
  ]);

  return (
    <haeo-forecast-card
      ref={ref}
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "calc(100vh - 56px)",
      }}
    />
  );
}

export const Default: Story = {
  render: (args) => {
    return <ForecastCardElementFrame args={args} />;
  },
};

export const FourHour: Story = {
  render: (args) => {
    return <ForecastCardElementFrame args={args} initialHorizon={4 * 60 * 60_000} />;
  },
};

export const Hovered: Story = {
  render: (args) => {
    return <ForecastCardElementFrame args={args} initialPointer={{ x: 520, y: 120 }} />;
  },
};

export const NarrowHovered: Story = {
  render: (args) => {
    return (
      <div style={{ width: "360px" }}>
        <ForecastCardElementFrame args={args} initialPointer={{ x: 220, y: 120 }} />
      </div>
    );
  },
};
