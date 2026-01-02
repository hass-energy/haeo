/**
 * Grid configuration form.
 */

import { useFlow } from "../../context/FlowContext";
import FormField from "./FormField";
import EntityPicker from "../EntityPicker";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { str, num, mode } from "./utils";
import "./Form.css";

function GridForm() {
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
          {isReconfigure ? "Edit Grid Connection" : "Add Grid Connection"}
        </h2>
        <p className="form__description">
          Configure your utility grid connection for import/export pricing and
          limits.
        </p>

        {error && (
          <div className="form__error" role="alert">
            {error}
          </div>
        )}

        <FormField
          id="name"
          label="Grid Name"
          required
          value={str(formData.name)}
          onChange={(value) => updateField("name", value)}
          placeholder="e.g., Utility Grid"
          disabled={isReconfigure}
        />

        <div className="form__section">
          <h3 className="form__section-title">Import Pricing</h3>

          <EntityPicker
            id="price_import"
            label="Import Price"
            mode={mode(formData.price_import_mode, "entity")}
            value={str(formData.price_import)}
            constantValue={num(formData.price_import_value, 0.3)}
            onChange={(newMode, value, constantValue) => {
              updateField("price_import_mode", newMode);
              updateField("price_import", value);
              if (constantValue !== undefined) {
                updateField("price_import_value", constantValue);
              }
            }}
            unit="$/kWh"
            required
            description="Entity providing import price or a constant rate."
          />

          <EntityPicker
            id="max_import_power"
            label="Max Import Power"
            mode={mode(formData.max_import_power_mode, "constant")}
            value={str(formData.max_import_power)}
            constantValue={num(formData.max_import_power_value, 100)}
            onChange={(newMode, value, constantValue) => {
              updateField("max_import_power_mode", newMode);
              updateField("max_import_power", value);
              if (constantValue !== undefined) {
                updateField("max_import_power_value", constantValue);
              }
            }}
            unit="kW"
            description="Maximum power import from the grid."
          />
        </div>

        <div className="form__section">
          <h3 className="form__section-title">Export Pricing</h3>

          <EntityPicker
            id="price_export"
            label="Export Price"
            mode={mode(formData.price_export_mode, "entity")}
            value={str(formData.price_export)}
            constantValue={num(formData.price_export_value, 0.05)}
            onChange={(newMode, value, constantValue) => {
              updateField("price_export_mode", newMode);
              updateField("price_export", value);
              if (constantValue !== undefined) {
                updateField("price_export_value", constantValue);
              }
            }}
            unit="$/kWh"
            description="Entity providing export price (feed-in tariff)."
          />

          <EntityPicker
            id="max_export_power"
            label="Max Export Power"
            mode={mode(formData.max_export_power_mode, "constant")}
            value={str(formData.max_export_power)}
            constantValue={num(formData.max_export_power_value, 5)}
            onChange={(newMode, value, constantValue) => {
              updateField("max_export_power_mode", newMode);
              updateField("max_export_power", value);
              if (constantValue !== undefined) {
                updateField("max_export_power_value", constantValue);
              }
            }}
            unit="kW"
            description="Maximum power export to the grid (feed-in limit)."
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
            description="Select the node this grid connection connects to."
          />
        </div>

        <div className="form__actions">
          <Button type="submit" variant="primary" loading={isSubmitting}>
            {isReconfigure ? "Save Changes" : "Add Grid"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default GridForm;
