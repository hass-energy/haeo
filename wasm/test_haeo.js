const { loadPyodide } = require("pyodide");
const path = require("path");
const fs = require("fs");

async function main() {
  console.log("Loading Pyodide...");
  const pyodide = await loadPyodide();
  await pyodide.loadPackage("micropip");
  
  const wheelPath = path.resolve("./highspy-1.14.0-cp312-cp312-pyodide_2024_0_wasm32.whl");
  await pyodide.runPythonAsync(`
import micropip
await micropip.install("numpy")
await micropip.install("typing-extensions")
await micropip.install("file://${wheelPath}")
`);

  // Mount HAEO core
  const haeoRoot = path.resolve("../haeo");
  function mount(src, dst) {
    pyodide.FS.mkdirTree(dst);
    for (const e of fs.readdirSync(src, { withFileTypes: true })) {
      if (e.name === "__pycache__" || e.name === "tests") continue;
      if (e.isDirectory()) mount(path.join(src, e.name), dst + "/" + e.name);
      else if (e.name.endsWith(".py")) pyodide.FS.writeFile(dst + "/" + e.name, fs.readFileSync(path.join(src, e.name), "utf8"));
    }
  }
  mount(path.join(haeoRoot, "custom_components/haeo/core"), "/haeo/custom_components/haeo/core");
  pyodide.FS.writeFile("/haeo/custom_components/__init__.py", "");
  pyodide.FS.writeFile("/haeo/custom_components/haeo/__init__.py", "");

  // Load scenario
  pyodide.globals.set("config_json", fs.readFileSync(path.join(haeoRoot, "tests/scenarios/scenario1/config.json"), "utf8"));
  pyodide.globals.set("inputs_json", fs.readFileSync(path.join(haeoRoot, "tests/scenarios/scenario1/inputs.json"), "utf8"));
  pyodide.globals.set("env_json", fs.readFileSync(path.join(haeoRoot, "tests/scenarios/scenario1/environment.json"), "utf8"));

  const result = await pyodide.runPythonAsync(`
import sys, json
sys.path.insert(0, "/haeo")
from datetime import datetime
import numpy as np

config = json.loads(config_json)
inputs_list = json.loads(inputs_json)
inputs = {e["entity_id"]: e for e in inputs_list}
env = json.loads(env_json)

from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.data.forecast_times import tiers_to_periods_seconds, generate_forecast_timestamps
from custom_components.haeo.core.data.loader.config_loader import load_element_configs
from custom_components.haeo.core.adapters.registry import collect_model_elements
from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.schema.elements.element_type import ElementType

class DictEntityState:
    def __init__(self, d):
        self._d = d
    @property
    def entity_id(self): return self._d.get("entity_id", "")
    @property
    def state(self): return self._d.get("state", "")
    @property
    def attributes(self): return self._d.get("attributes", {})
    def as_dict(self): return self._d

class ScenarioSM:
    def __init__(self, data):
        self._s = {k: DictEntityState(v) for k, v in data.items()}
    def get(self, eid):
        return self._s.get(eid)

frozen_dt = datetime.fromisoformat(env["optimization_start_time"])
periods_seconds = tiers_to_periods_seconds(config, start_time=frozen_dt)
periods_hours = np.asarray(periods_seconds, dtype=float) / 3600
forecast_times = generate_forecast_timestamps(periods_seconds, start_time=frozen_dt.timestamp())

sm = ScenarioSM(inputs)
loaded_configs = load_element_configs(config["participants"], sm, forecast_times)

network = Network(name="browser", periods=periods_hours)
model_elements = list(collect_model_elements(loaded_configs))

policy_rules = []
for name, cfg in loaded_configs.items():
    if cfg.get("element_type") == ElementType.POLICY:
        from custom_components.haeo.core.adapters.elements.policy import extract_policy_rules
        policy_rules.extend(extract_policy_rules(cfg))

compiled = compile_policies(model_elements, policy_rules)
for elem in compiled["elements"]:
    network.add(elem)

print(f"Network: {len(network.elements)} elements, {len(periods_hours)} periods")
objective = network.optimize()
print(f"Objective: {objective:.4f}")
f"SOLVED: {len(network.elements)} elements, obj={objective:.4f}"
`);

  console.log(result);
  console.log("✅ HAEO optimization complete in Pyodide WASM!");
}

main().catch(e => { console.error(e.message?.split("\n").slice(-5).join("\n") || e); process.exit(1); });
