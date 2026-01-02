/**
 * Inverter configuration form.
 */

import { useFlow } from "../../context/FlowContext";
import FormField from "./FormField";
import EntityPicker from "../EntityPicker";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { str, num, mode } from "./utils";
import "./Form.css";

function InverterForm() {
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
          {isReconfigure ? "Edit Inverter" : "Add Inverter"}
        </h2>
        <p className="form__description">
          Configure a DC/AC inverter connecting DC sources (solar, battery) to
          AC loads.
        </p>

        {error && (
          <div className="form__error" role="alert">
            {error}
          </div>
        )}

        <FormField
          id="name"
          label="Inverter Name"
          required
          value={str(formData.name)}
          onChange={(value) => updateField("name", value)}
          placeholder="e.g., Hybrid Inverter"
          disabled={isReconfigure}
        />

        <div className="form__section">
          <h3 className="form__section-title">Power Rating</h3>

          <EntityPicker
            id="max_power"
            label="Max Power"
            mode={mode(formData.max_power_mode, "constant")}
            value={str(formData.max_power)}
            constantValue={num(formData.max_power_value, 5)}
            onChange={(newMode, value, constantValue) => {
              updateField("max_power_mode", newMode);
              updateField("max_power", value);
              if (constantValue !== undefined) {
                updateField("max_power_value", constantValue);
              }
            }}
            unit="kW"
            description="Maximum continuous power rating."
          />
        </div>

        <div className="form__section">
          <h3 className="form__section-title">Efficiency</h3>

          <EntityPicker
            id="efficiency"
            label="Conversion Efficiency"
            mode={mode(formData.efficiency_mode, "constant")}
            value={str(formData.efficiency)}
            constantValue={num(formData.efficiency_value, 97)}
            onChange={(newMode, value, constantValue) => {
              updateField("efficiency_mode", newMode);
              updateField("efficiency", value);
              if (constantValue !== undefined) {
                updateField("efficiency_value", constantValue);
              }
            }}
            unit="%"
            description="DC to AC conversion efficiency."
          />
        </div>

        <div className="form__section">
          <h3 className="form__section-title">Connections</h3>

          <FormField
            id="dc_connection"
            label="DC Side (Input)"
            type="select"
            required
            value={str(formData.dc_connection)}
            onChange={(value) => updateField("dc_connection", value)}
            options={[
              { value: "", label: "Select a node..." },
              // TODO: Populate with available nodes from the network
            ]}
            description="Node for DC connections (solar, battery)."
          />

          <FormField
            id="ac_connection"
            label="AC Side (Output)"
            type="select"
            required
            value={str(formData.ac_connection)}
            onChange={(value) => updateField("ac_connection", value)}
            options={[
              { value: "", label: "Select a node..." },
              // TODO: Populate with available nodes from the network
            ]}
            description="Node for AC connections (grid, loads)."
          />
        </div>

        <div className="form__actions">
          <Button type="submit" variant="primary" loading={isSubmitting}>
            {isReconfigure ? "Save Changes" : "Add Inverter"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default InverterForm;
