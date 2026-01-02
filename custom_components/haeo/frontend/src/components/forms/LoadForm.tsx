/**
 * Load configuration form (constant or forecast load).
 */

import { useFlow } from "../../context/FlowContext";
import FormField from "./FormField";
import EntityPicker from "../EntityPicker";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { str, num } from "./utils";
import "./Form.css";

const LOAD_TYPES = [
  { value: "forecast", label: "Forecast Load (from sensor)" },
  { value: "constant", label: "Constant Load (fixed value)" },
];

function LoadForm() {
  const { params, formData, updateField, submit, isSubmitting, error } =
    useFlow();

  const isReconfigure = params?.source === "reconfigure";
  const loadType = str(formData.load_type, "forecast");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit();
  };

  return (
    <Card>
      <form className="form" onSubmit={handleSubmit}>
        <h2 className="form__title">
          {isReconfigure ? "Edit Load" : "Add Load"}
        </h2>
        <p className="form__description">
          Configure an electrical load that consumes power from the network.
        </p>

        {error && (
          <div className="form__error" role="alert">
            {error}
          </div>
        )}

        <FormField
          id="name"
          label="Load Name"
          required
          value={str(formData.name)}
          onChange={(value) => updateField("name", value)}
          placeholder="e.g., House Load"
          disabled={isReconfigure}
        />

        <FormField
          id="load_type"
          label="Load Type"
          type="select"
          required
          value={loadType}
          onChange={(value) => updateField("load_type", value)}
          options={LOAD_TYPES}
          description="How the load demand is determined."
        />

        <div className="form__section">
          <h3 className="form__section-title">Load Configuration</h3>

          {loadType === "forecast" ? (
            <EntityPicker
              id="forecast"
              label="Load Forecast"
              mode="entity"
              value={str(formData.forecast)}
              onChange={(_mode, value) => {
                updateField("forecast", value);
              }}
              unit="kW"
              required
              description="Entity providing load consumption forecast."
            />
          ) : (
            <EntityPicker
              id="power"
              label="Constant Power"
              mode="constant"
              value={str(formData.power)}
              constantValue={num(formData.power_value, 1)}
              onChange={(_mode, value, constantValue) => {
                updateField("power", value);
                if (constantValue !== undefined) {
                  updateField("power_value", constantValue);
                }
              }}
              unit="kW"
              required
              description="Fixed power consumption."
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
            description="Select the node this load connects to."
          />
        </div>

        <div className="form__actions">
          <Button type="submit" variant="primary" loading={isSubmitting}>
            {isReconfigure ? "Save Changes" : "Add Load"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default LoadForm;
