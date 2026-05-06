/**
 * Live WASM Optimization Story
 *
 * Runs HAEO's optimization engine in-browser via Pyodide (Python in WASM).
 * Loads scenario config+inputs, solves the LP, and renders the forecast card
 * with the live results.
 */
import type { Meta, StoryObj } from "@storybook/preact";
import { useEffect, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";

import "../card";
import type { ForecastCardConfig } from "../types";
import type { HassLike } from "../series";

// Pyodide type declarations
interface Pyodide {
  loadPackage(name: string): Promise<void>;
  runPythonAsync(code: string): Promise<string>;
  globals: { set(key: string, value: string): void };
}

declare global {
  function loadPyodide(): Promise<Pyodide>;
}

// Load scenario inputs (config + inputs + environment)
const scenarioInputModules = import.meta.glob<Record<string, unknown>>(
  "../../../../tests/scenarios/scenario*/config.json",
  { eager: true, import: "default" }
);
const scenarioEnvModules = import.meta.glob<Record<string, unknown>>(
  "../../../../tests/scenarios/scenario*/environment.json",
  { eager: true, import: "default" }
);
const scenarioInputDataModules = import.meta.glob<unknown[]>("../../../../tests/scenarios/scenario*/inputs.json", {
  eager: true,
  import: "default",
});

function scenarioName(path: string): string | null {
  const m = /\/(scenario\d+)\//.exec(path);
  return m ? (m[1] ?? null) : null;
}

const SCENARIOS = [
  ...new Set(
    Object.keys(scenarioInputModules)
      .map(scenarioName)
      .filter((s): s is string => s !== null)
  ),
].sort((a, b) => Number(a.replace("scenario", "")) - Number(b.replace("scenario", "")));

interface StoryArgs {
  scenario: string;
}

const meta: Meta<StoryArgs> = {
  title: "Live/WASMOptimization",
  args: { scenario: SCENARIOS[0] ?? "scenario1" },
  argTypes: {
    scenario: { control: { type: "inline-radio" }, options: SCENARIOS },
  },
};

export default meta;
type Story = StoryObj<StoryArgs>;

// Pyodide solver Python code
const SOLVER_PY = `
import json
from datetime import datetime
import numpy as np

from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.data.forecast_times import tiers_to_periods_seconds, generate_forecast_timestamps
from custom_components.haeo.core.data.loader.config_loader import load_element_configs
from custom_components.haeo.core.adapters.registry import collect_model_elements
from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.schema.elements.element_type import ElementType

class _S:
    def __init__(self, d):
        self._d = d
    @property
    def entity_id(self): return self._d.get("entity_id", "")
    @property
    def state(self): return self._d.get("state", "")
    @property
    def attributes(self): return self._d.get("attributes", {})
    def as_dict(self): return self._d

class _SM:
    def __init__(self, data):
        self._s = {k: _S(v) for k, v in data.items()}
    def get(self, eid): return self._s.get(eid)

def solve_scenario(cfg_json, inp_json, env_json):
    cfg = json.loads(cfg_json)
    inp = {e["entity_id"]: e for e in json.loads(inp_json)}
    env = json.loads(env_json)

    frozen = datetime.fromisoformat(env["optimization_start_time"])
    ps = tiers_to_periods_seconds(cfg, start_time=frozen)
    ph = np.asarray(ps, dtype=float) / 3600
    ft = generate_forecast_timestamps(ps, start_time=frozen.timestamp())

    lc = load_element_configs(cfg["participants"], _SM(inp), ft)
    net = Network(name="browser", periods=ph)
    me = list(collect_model_elements(lc))

    pr = []
    for n, c in lc.items():
        if c.get("element_type") == ElementType.POLICY:
            from custom_components.haeo.core.adapters.elements.policy import extract_policy_rules
            pr.extend(extract_policy_rules(c))

    comp = compile_policies(me, pr)
    for e in comp["elements"]:
        net.add(e)

    obj = net.optimize()

    # Build output states matching HA sensor format
    states = {}
    for name, element in net.elements.items():
        for oname in element.output_names:
            method = getattr(element, oname, None)
            if not callable(method):
                continue
            try:
                val = method()
                if not hasattr(val, "state"):
                    continue
                state = val.state
                entity_id = f"sensor.{name.lower().replace(':', '_')}_{oname}"
                attrs = {
                    "element_name": name.split(":")[0],
                    "element_type": "node",
                    "output_name": oname,
                    "field_type": val.type if hasattr(val, "type") else "unknown",
                    "source_role": "output",
                }
                if isinstance(state, (list, np.ndarray)):
                    forecast = [{"value": float(v)} for v in state]
                    attrs["forecast"] = forecast
                    state_val = str(float(state[0])) if len(state) > 0 else "0"
                else:
                    state_val = str(state) if state is not None else "0"
                states[entity_id] = {
                    "state": state_val,
                    "attributes": attrs,
                    "entity_id": entity_id,
                }
            except Exception:
                pass

    return json.dumps({"objective": obj, "elements": len(net.elements), "periods": len(ph), "states": states})

print("HAEO WASM solver ready")
`;

function WasmDemo({ scenario }: StoryArgs): JSX.Element {
  const [status, setStatus] = useState<string>("Loading Pyodide...");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    objective: number;
    elements: number;
    periods: number;
    elapsed: number;
  } | null>(null);
  const [hass, setHass] = useState<HassLike | null>(null);
  const cardRef = useRef<HTMLElement>(null);
  const pyodideRef = useRef<Pyodide | null>(null);

  // Initialize Pyodide
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      if (pyodideRef.current != null) return;
      try {
        setStatus("Loading Pyodide runtime...");
        const pyodide = await loadPyodide();
        if (cancelled) return;

        setStatus("Installing packages...");
        await pyodide.loadPackage("micropip");
        await pyodide.runPythonAsync(`
import micropip
await micropip.install("numpy")
await micropip.install("typing-extensions")
await micropip.install("./highspy-1.14.0-cp312-cp312-pyodide_2024_0_wasm32.whl")
await micropip.install("./haeo_core-0.4.0-py3-none-any.whl", deps=False)
`);
        await pyodide.runPythonAsync(SOLVER_PY);
        pyodideRef.current = pyodide;
        if (!cancelled) setStatus("Ready");
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Run optimization when scenario changes
  useEffect(() => {
    if (pyodideRef.current == null) return;
    const pyodide = pyodideRef.current;

    const configPath = Object.keys(scenarioInputModules).find((p) => scenarioName(p) === scenario);
    const envPath = Object.keys(scenarioEnvModules).find((p) => scenarioName(p) === scenario);
    const inputsPath = Object.keys(scenarioInputDataModules).find((p) => scenarioName(p) === scenario);
    if (configPath == null || envPath == null || inputsPath == null) return;

    setStatus(`Optimizing ${scenario}...`);
    setResult(null);

    const t0 = performance.now();
    const cfgJson = JSON.stringify(scenarioInputModules[configPath]);
    const envJson = JSON.stringify(scenarioEnvModules[envPath]);
    const inpJson = JSON.stringify(scenarioInputDataModules[inputsPath]);

    pyodide.globals.set("cfg_json", cfgJson);
    pyodide.globals.set("inp_json", inpJson);
    pyodide.globals.set("env_json", envJson);

    void pyodide
      .runPythonAsync(`solve_scenario(cfg_json, inp_json, env_json)`)
      .then((resultJson: string) => {
        const elapsed = (performance.now() - t0) / 1000;
        const data = JSON.parse(resultJson) as {
          objective: number;
          elements: number;
          periods: number;
          states: Record<string, unknown>;
        };
        setResult({ ...data, elapsed });
        setHass({ states: data.states as HassLike["states"] });
        setStatus(`Solved in ${elapsed.toFixed(2)}s`);
      })
      .catch((e: unknown) => setError(String(e)));
  }, [scenario, pyodideRef.current]);

  // Update card when hass changes
  useEffect(() => {
    if (cardRef.current == null || hass == null) return;
    const card = cardRef.current as HTMLElement & {
      setConfig: (c: ForecastCardConfig) => void;
      hass: HassLike | null;
    };
    card.setConfig({ type: "custom:haeo-forecast-card" });
    card.hass = hass;
  }, [hass]);

  if (error != null) {
    return <div style={{ color: "red", padding: "20px" }}>Error: {error}</div>;
  }

  return (
    <div style={{ padding: "16px" }}>
      <div
        style={{
          marginBottom: "16px",
          padding: "12px",
          borderRadius: "8px",
          background: result != null ? "#1b3a1b" : "#2a2a4e",
          color: result != null ? "#4CAF50" : "#aaa",
          fontSize: "14px",
        }}
      >
        {status}
        {result != null && (
          <span style={{ marginLeft: "16px", color: "#888" }}>
            {result.elements} elements · {result.periods} periods · obj: ${result.objective.toFixed(2)}
          </span>
        )}
      </div>
      <div style={{ minHeight: "400px" }}>
        <haeo-forecast-card ref={cardRef} />
      </div>
    </div>
  );
}

export const Default: Story = {
  render: (args) => <WasmDemo {...args} />,
  parameters: {
    // Load Pyodide from CDN
    docs: { description: { story: "Runs HAEO optimization in-browser via Pyodide WASM" } },
  },
};
