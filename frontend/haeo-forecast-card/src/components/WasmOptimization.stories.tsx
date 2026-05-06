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

// Load solver shim source at build time
const solverShimSource = import.meta.glob("../../../../wasm/solver_shim.py", { eager: true, query: "?raw", import: "default" });
const SOLVER_PY = Object.values(solverShimSource)[0] as string;

// Discover wheel filenames from wasm/dist/ at build time
const wheelFiles = import.meta.glob("../../../../wasm/dist/*.whl", { eager: true, query: "?url", import: "default" });
const WHEEL_URLS = Object.values(wheelFiles) as string[];

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

        // Install wheels discovered at build time
        const wheelInstalls = WHEEL_URLS.map((url) => {
          const isHaeoCore = url.includes("haeo_core");
          return `await micropip.install("${url}"${isHaeoCore ? ", deps=False" : ""})`;
        }).join("\n");

        await pyodide.runPythonAsync(`
import micropip
await micropip.install("numpy")
await micropip.install("typing-extensions")
${wheelInstalls}
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
