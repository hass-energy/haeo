/**
 * Connection configuration form.
 */

import { useFlow } from "../../context/FlowContext";
import FormField from "./FormField";
import EntityPicker from "../EntityPicker";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { str, num, bool, mode } from "./utils";
import "./Form.css";

function ConnectionForm() {
  const { params, formData, updateField, submit, isSubmitting, error } =
    useFlow();

  const isReconfigure = params?.source === "reconfigure";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit();
  };

  return (
    <Card>
      <form className="form" onSubmit={handleSubmit}>
        <h2 className="form__title">
          {isReconfigure ? "Edit Connection" : "Add Connection"}
        </h2>
        <p className="form__description">
          Create a power connection between two nodes with optional limits and
          efficiency.
        </p>

        {error && (
          <div className="form__error" role="alert">
            {error}
          </div>
        )}

        <FormField
          id="name"
          label="Connection Name"
          required
          value={str(formData.name)}
          onChange={(value) => updateField("name", value)}
          placeholder="e.g., DC Bus Link"
          disabled={isReconfigure}
        />

        <div className="form__section">
          <h3 className="form__section-title">Connection Points</h3>

          <div className="form__row">
            <FormField
              id="source"
              label="Source Node"
              type="select"
              required
              value={str(formData.source)}
              onChange={(value) => updateField("source", value)}
              options={[
                { value: "", label: "Select a node..." },
                // TODO: Populate with available nodes from the network
              ]}
              description="Power flows from this node."
            />

            <FormField
              id="target"
              label="Target Node"
              type="select"
              required
              value={str(formData.target)}
              onChange={(value) => updateField("target", value)}
              options={[
                { value: "", label: "Select a node..." },
                // TODO: Populate with available nodes from the network
              ]}
              description="Power flows to this node."
            />
          </div>
        </div>

        <div className="form__section">
          <h3 className="form__section-title">Power Limits</h3>

          <EntityPicker
            id="max_power"
            label="Max Power"
            mode={mode(formData.max_power_mode, "constant")}
            value={str(formData.max_power)}
            constantValue={num(formData.max_power_value, 100)}
            onChange={(newMode, value, constantValue) => {
              updateField("max_power_mode", newMode);
              updateField("max_power", value);
              if (constantValue !== undefined) {
                updateField("max_power_value", constantValue);
              }
            }}
            unit="kW"
            description="Maximum power flow through this connection."
          />

          <FormField
            id="bidirectional"
            label="Bidirectional"
            type="checkbox"
            value={bool(formData.bidirectional, true)}
            onChange={(value) => updateField("bidirectional", value)}
            description="Allow power to flow in both directions."
          />
        </div>

        <div className="form__section">
          <h3 className="form__section-title">Efficiency & Cost</h3>

          <EntityPicker
            id="efficiency"
            label="Transfer Efficiency"
            mode={mode(formData.efficiency_mode, "constant")}
            value={str(formData.efficiency)}
            constantValue={num(formData.efficiency_value, 100)}
            onChange={(newMode, value, constantValue) => {
              updateField("efficiency_mode", newMode);
              updateField("efficiency", value);
              if (constantValue !== undefined) {
                updateField("efficiency_value", constantValue);
              }
            }}
            unit="%"
            description="Efficiency of power transfer (100% = no losses)."
          />

          <EntityPicker
            id="cost"
            label="Transfer Cost"
            mode={mode(formData.cost_mode, "constant")}
            value={str(formData.cost)}
            constantValue={num(formData.cost_value, 0)}
            onChange={(newMode, value, constantValue) => {
              updateField("cost_mode", newMode);
              updateField("cost", value);
              if (constantValue !== undefined) {
                updateField("cost_value", constantValue);
              }
            }}
            unit="$/kWh"
            description="Cost per kWh of power transferred."
          />
        </div>

        <div className="form__actions">
          <Button type="submit" variant="primary" loading={isSubmitting}>
            {isReconfigure ? "Save Changes" : "Add Connection"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default ConnectionForm;
