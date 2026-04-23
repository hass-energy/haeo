import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { HassEntityState, HassLike } from "../series";

function scenarioPath(name: string): string {
  return resolve(import.meta.dirname, "../../../../tests/scenarios", name, "outputs.json");
}

export function loadScenarioHassState(name: string): HassLike {
  const file = readFileSync(scenarioPath(name), "utf-8");
  const parsed = JSON.parse(file) as Record<string, HassEntityState>;
  return { states: parsed };
}
