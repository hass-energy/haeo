import type { HassEntityState, HassLike } from "../series";

export type StoryDataMode = "mixed" | "inputs" | "outputs";

type ScenarioStates = Record<string, HassEntityState | undefined>;

const scenarioModules = import.meta.glob<ScenarioStates>("../../../../tests/scenarios/scenario*/outputs.json", {
  eager: true,
  import: "default",
});

function scenarioNameFromPath(path: string): string | null {
  const match = /\/(scenario\d+)\/outputs\.json$/.exec(path);
  return match ? (match[1] ?? null) : null;
}

const SCENARIO_FIXTURES: Record<string, HassLike> = Object.fromEntries(
  Object.entries(scenarioModules)
    .map(([path, moduleValue]) => {
      const scenario = scenarioNameFromPath(path);
      if (scenario === null) {
        return null;
      }
      return [scenario, { states: moduleValue }];
    })
    .filter((entry): entry is [string, HassLike] => entry !== null)
);

export type StoryScenario = string;

export const STORY_SCENARIOS: StoryScenario[] = Object.keys(SCENARIO_FIXTURES).sort(
  (a, b) => Number(a.replace("scenario", "")) - Number(b.replace("scenario", ""))
);

export function getScenarioFixture(scenario: StoryScenario, mode: StoryDataMode): HassLike {
  const fixture = SCENARIO_FIXTURES[scenario];
  if (!fixture) {
    return { states: {} };
  }
  if (mode === "mixed") {
    return fixture;
  }
  const states = Object.fromEntries(
    Object.entries(fixture.states).filter(([, state]) => {
      const attrs = (state?.attributes ?? {}) as { forecast?: unknown; config_mode?: unknown };
      const hasForecast = Array.isArray(attrs.forecast) && attrs.forecast.length > 1;
      if (!hasForecast) {
        return false;
      }
      const isInput = attrs.config_mode !== undefined && attrs.config_mode !== null;
      return mode === "inputs" ? isInput : !isInput;
    })
  ) as Record<string, HassEntityState | undefined>;
  return { states };
}
