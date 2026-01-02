/**
 * Solar/Photovoltaics configuration form.
 */

import { useFlow } from "../../context/FlowContext";
import FormField from "./FormField";
import EntityPicker from "../EntityPicker";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { str, num, bool, mode } from "./utils";
import "./Form.css";

function SolarForm() {
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
          {isReconfigure ? "Edit Solar Array" : "Add Solar Array"}
        </h2>
        <p className="form__description">
          Configure your solar generation source with forecast data.
        </p>

        {error && (
          <div className="form__error" role="alert">
            {error}
          </div>
        )}

        <FormField
          id="name"
          label="Solar Array Name"
          required
          value={str(formData.name)}
          onChange={(value) => updateField("name", value)}
          placeholder="e.g., Roof Panels"
          disabled={isReconfigure}
        />

        <div className="form__section">
          <h3 className="form__section-title">Generation Forecast</h3>

          <EntityPicker
            id="forecast"
            label="Solar Forecast"
            mode="entity"
            value={str(formData.forecast)}
            onChange={(_mode, value) => {
              updateField("forecast", value);
            }}
            unit="kW"
            required
            description="Entity providing solar generation forecast (e.g., Solcast, OpenMeteo)."
          />
        </div>

        <div className="form__section">
          <h3 className="form__section-title">Curtailment (Optional)</h3>

          <FormField
            id="allow_curtailment"
            label="Allow Curtailment"
            type="checkbox"
            value={bool(formData.allow_curtailment, false)}
            onChange={(value) => updateField("allow_curtailment", value)}
            description="Enable the optimizer to curtail (reduce) solar generation if beneficial."
          />

          {bool(formData.allow_curtailment, false) && (
            <EntityPicker
              id="curtailment_cost"
              label="Curtailment Cost"
              mode={mode(formData.curtailment_cost_mode, "constant")}
              value={str(formData.curtailment_cost)}
              constantValue={num(formData.curtailment_cost_value, 0)}
              onChange={(newMode, value, constantValue) => {
                updateField("curtailment_cost_mode", newMode);
                updateField("curtailment_cost", value);
                if (constantValue !== undefined) {
                  updateField("curtailment_cost_value", constantValue);
                }
              }}
              unit="$/kWh"
              description="Cost per kWh of curtailed generation (0 = free curtailment)."
            />
          )}
        </div>

        <div className="form__section">
          <h3 className="form__section-title">Network Connection</h3>

          <FormField
            id="connection"
            label="Connect To"
            type="select"
            required
            value={str(formData.connection)}
            onChange={(value) => updateField("connection", value)}
            options={[
              { value: "", label: "Select a node..." },
              // TODO: Populate with available nodes from the network
            ]}
            description="Select the node this solar array connects to."
          />
        </div>

        <div className="form__actions">
          <Button type="submit" variant="primary" loading={isSubmitting}>
            {isReconfigure ? "Save Changes" : "Add Solar"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default SolarForm;
