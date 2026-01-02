/**
 * Battery configuration form.
 */

import { useFlow } from "../../context/FlowContext";
import FormField from "./FormField";
import EntityPicker from "../EntityPicker";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { str, num, mode } from "./utils";
import "./Form.css";

function BatteryForm() {
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
          {isReconfigure ? "Edit Battery" : "Add Battery"}
        </h2>
        <p className="form__description">
          Configure your battery storage system for energy optimization.
        </p>

        {error && (
          <div className="form__error" role="alert">
            {error}
          </div>
        )}

        <FormField
          id="name"
          label="Battery Name"
          required
          value={str(formData.name)}
          onChange={(value) => updateField("name", value)}
          placeholder="e.g., Powerwall"
          disabled={isReconfigure}
        />

        <div className="form__section">
          <h3 className="form__section-title">Capacity & Power</h3>

          <EntityPicker
            id="capacity"
            label="Capacity"
            mode={mode(formData.capacity_mode, "constant")}
            value={str(formData.capacity)}
            constantValue={num(formData.capacity_value, 13.5)}
            onChange={(newMode, value, constantValue) => {
              updateField("capacity_mode", newMode);
              updateField("capacity", value);
              if (constantValue !== undefined) {
                updateField("capacity_value", constantValue);
              }
            }}
            unit="kWh"
            description="Total usable energy capacity of the battery."
          />

          <EntityPicker
            id="max_charge_power"
            label="Max Charge Power"
            mode={mode(formData.max_charge_power_mode, "constant")}
            value={str(formData.max_charge_power)}
            constantValue={num(formData.max_charge_power_value, 5)}
            onChange={(newMode, value, constantValue) => {
              updateField("max_charge_power_mode", newMode);
              updateField("max_charge_power", value);
              if (constantValue !== undefined) {
                updateField("max_charge_power_value", constantValue);
              }
            }}
            unit="kW"
            description="Maximum power when charging."
          />

          <EntityPicker
            id="max_discharge_power"
            label="Max Discharge Power"
            mode={mode(formData.max_discharge_power_mode, "constant")}
            value={str(formData.max_discharge_power)}
            constantValue={num(formData.max_discharge_power_value, 5)}
            onChange={(newMode, value, constantValue) => {
              updateField("max_discharge_power_mode", newMode);
              updateField("max_discharge_power", value);
              if (constantValue !== undefined) {
                updateField("max_discharge_power_value", constantValue);
              }
            }}
            unit="kW"
            description="Maximum power when discharging."
          />
        </div>

        <div className="form__section">
          <h3 className="form__section-title">State of Charge</h3>

          <EntityPicker
            id="soc"
            label="Current SOC"
            mode="entity"
            value={str(formData.soc)}
            onChange={(_mode, value) => {
              updateField("soc", value);
            }}
            unit="%"
            required
            description="Entity providing the current state of charge."
          />

          <div className="form__row">
            <FormField
              id="min_soc"
              label="Minimum SOC"
              type="number"
              value={num(formData.min_soc, 10)}
              onChange={(value) => updateField("min_soc", value)}
              min={0}
              max={100}
              description="Never discharge below this level (%)"
            />
            <FormField
              id="max_soc"
              label="Maximum SOC"
              type="number"
              value={num(formData.max_soc, 100)}
              onChange={(value) => updateField("max_soc", value)}
              min={0}
              max={100}
              description="Never charge above this level (%)"
            />
          </div>
        </div>

        <div className="form__section">
          <h3 className="form__section-title">Efficiency</h3>

          <EntityPicker
            id="charge_efficiency"
            label="Charge Efficiency"
            mode={mode(formData.charge_efficiency_mode, "constant")}
            value={str(formData.charge_efficiency)}
            constantValue={num(formData.charge_efficiency_value, 95)}
            onChange={(newMode, value, constantValue) => {
              updateField("charge_efficiency_mode", newMode);
              updateField("charge_efficiency", value);
              if (constantValue !== undefined) {
                updateField("charge_efficiency_value", constantValue);
              }
            }}
            unit="%"
            description="Percentage of input power stored."
          />

          <EntityPicker
            id="discharge_efficiency"
            label="Discharge Efficiency"
            mode={mode(formData.discharge_efficiency_mode, "constant")}
            value={str(formData.discharge_efficiency)}
            constantValue={num(formData.discharge_efficiency_value, 95)}
            onChange={(newMode, value, constantValue) => {
              updateField("discharge_efficiency_mode", newMode);
              updateField("discharge_efficiency", value);
              if (constantValue !== undefined) {
                updateField("discharge_efficiency_value", constantValue);
              }
            }}
            unit="%"
            description="Percentage of stored energy delivered."
          />
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
            description="Select the node this battery connects to."
          />
        </div>

        <div className="form__actions">
          <Button type="submit" variant="primary" loading={isSubmitting}>
            {isReconfigure ? "Save Changes" : "Add Battery"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default BatteryForm;
