const { loadPyodide } = require("pyodide");
const path = require("path");
const fs = require("fs");

async function main() {
  console.time("total");
  console.log("Loading Pyodide...");
  console.time("pyodide");
  const pyodide = await loadPyodide();
  await pyodide.loadPackage("micropip");
  console.timeEnd("pyodide");
  
  console.time("install");
  const highspyWhl = path.resolve("./highspy-1.14.0-cp312-cp312-pyodide_2024_0_wasm32.whl");
  const haeoWhl = path.resolve("./haeo_core-0.4.0-py3-none-any.whl");
  
  await pyodide.runPythonAsync(`
import micropip
await micropip.install("numpy")
await micropip.install("typing-extensions")
await micropip.install("file://${highspyWhl}")
await micropip.install("file://${haeoWhl}", deps=False)
`);
  console.timeEnd("install");

  // Load all 6 scenarios
  const haeoRoot = path.resolve("../haeo");
  const scenarios = [];
  for (let i = 1; i <= 6; i++) {
    const dir = path.join(haeoRoot, `tests/scenarios/scenario${i}`);
    if (!fs.existsSync(dir)) continue;
    scenarios.push({
      name: `scenario${i}`,
      config: fs.readFileSync(path.join(dir, "config.json"), "utf8"),
      inputs: fs.readFileSync(path.join(dir, "inputs.json"), "utf8"),
      env: fs.readFileSync(path.join(dir, "environment.json"), "utf8"),
    });
  }
  
  for (const s of scenarios) {
    pyodide.globals.set("cfg_json", s.config);
    pyodide.globals.set("inp_json", s.inputs);
    pyodide.globals.set("env_json", s.env);
    
    console.time(s.name);
    const result = await pyodide.runPythonAsync(`
import sys, json
from datetime import datetime
import numpy as np

cfg = json.loads(cfg_json)
inp_list = json.loads(inp_json)
inp = {e["entity_id"]: e for e in inp_list}
env = json.loads(env_json)

from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.data.forecast_times import tiers_to_periods_seconds, generate_forecast_timestamps
from custom_components.haeo.core.data.loader.config_loader import load_element_configs
from custom_components.haeo.core.adapters.registry import collect_model_elements
from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.schema.elements.element_type import ElementType

class S:
    def __init__(self, d):
        self._d = d
    @property
    def entity_id(self): return self._d.get("entity_id", "")
    @property
    def state(self): return self._d.get("state", "")
    @property
    def attributes(self): return self._d.get("attributes", {})
    def as_dict(self): return self._d

class SM:
    def __init__(self, data):
        self._s = {k: S(v) for k, v in data.items()}
    def get(self, eid): return self._s.get(eid)

frozen = datetime.fromisoformat(env["optimization_start_time"])
ps = tiers_to_periods_seconds(cfg, start_time=frozen)
ph = np.asarray(ps, dtype=float) / 3600
ft = generate_forecast_timestamps(ps, start_time=frozen.timestamp())

lc = load_element_configs(cfg["participants"], SM(inp), ft)
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
f"{len(net.elements)} elements, {len(ph)} periods, obj={obj:.4f}"
`);
    console.timeEnd(s.name);
    console.log(`  ${s.name}: ${result}`);
  }
  
  console.timeEnd("total");
  console.log("\n✅ All scenarios solved in Pyodide WASM!");
}

main().catch(e => { console.error(e.message?.split("\n").slice(-5).join("\n") || e); process.exit(1); });
