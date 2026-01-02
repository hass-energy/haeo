/**
 * Hub configuration form.
 */

import { useFlow } from "../../context/FlowContext";
import FormField from "./FormField";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { str, num, bool } from "./utils";
import "./Form.css";

const HORIZON_PRESETS = [
  { value: "2_days", label: "2 Days" },
  { value: "3_days", label: "3 Days" },
  { value: "5_days", label: "5 Days (Recommended)" },
  { value: "7_days", label: "7 Days" },
  { value: "custom", label: "Custom" },
];

function HubForm() {
  const { formData, updateField, submit, isSubmitting, error } = useFlow();

  const isCustom = str(formData.horizon_preset, "5_days") === "custom";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit();
  };

  return (
    <Card>
      <form className="form" onSubmit={handleSubmit}>
        <h2 className="form__title">HAEO Network Setup</h2>
        <p className="form__description">
          Configure your energy optimization network. You can add batteries,
          solar panels, and other elements after setup.
        </p>

        {error && (
          <div className="form__error" role="alert">
            {error}
          </div>
        )}

        <FormField
          id="name"
          label="Network Name"
          required
          value={str(formData.name)}
          onChange={(value) => updateField("name", value)}
          placeholder="e.g., Home Energy System"
        />

        <FormField
          id="horizon_preset"
          label="Optimization Horizon"
          type="select"
          required
          value={str(formData.horizon_preset, "5_days")}
          onChange={(value) => updateField("horizon_preset", value)}
          options={HORIZON_PRESETS}
          description="How far ahead to optimize. Longer horizons provide better planning but require more forecast data."
        />

        {isCustom && (
          <div className="form__group">
            <h3 className="form__group-title">Custom Tier Configuration</h3>
            <p className="form__group-description">
              Configure the time resolution tiers for optimization.
            </p>

            <div className="form__row">
              <FormField
                id="tier_1_count"
                label="Tier 1 Count"
                type="number"
                value={num(formData.tier_1_count, 5)}
                onChange={(value) => updateField("tier_1_count", Number(value))}
                min={1}
                max={60}
              />
              <FormField
                id="tier_1_duration"
                label="Tier 1 Duration (min)"
                type="number"
                value={num(formData.tier_1_duration, 1)}
                onChange={(value) =>
                  updateField("tier_1_duration", Number(value))
                }
                min={1}
                max={60}
              />
            </div>

            <div className="form__row">
              <FormField
                id="tier_2_count"
                label="Tier 2 Count"
                type="number"
                value={num(formData.tier_2_count, 11)}
                onChange={(value) => updateField("tier_2_count", Number(value))}
                min={1}
                max={60}
              />
              <FormField
                id="tier_2_duration"
                label="Tier 2 Duration (min)"
                type="number"
                value={num(formData.tier_2_duration, 5)}
                onChange={(value) =>
                  updateField("tier_2_duration", Number(value))
                }
                min={1}
                max={60}
              />
            </div>

            <div className="form__row">
              <FormField
                id="tier_3_count"
                label="Tier 3 Count"
                type="number"
                value={num(formData.tier_3_count, 46)}
                onChange={(value) => updateField("tier_3_count", Number(value))}
                min={1}
                max={100}
              />
              <FormField
                id="tier_3_duration"
                label="Tier 3 Duration (min)"
                type="number"
                value={num(formData.tier_3_duration, 30)}
                onChange={(value) =>
                  updateField("tier_3_duration", Number(value))
                }
                min={1}
                max={120}
              />
            </div>

            <div className="form__row">
              <FormField
                id="tier_4_count"
                label="Tier 4 Count"
                type="number"
                value={num(formData.tier_4_count, 48)}
                onChange={(value) => updateField("tier_4_count", Number(value))}
                min={1}
                max={168}
              />
              <FormField
                id="tier_4_duration"
                label="Tier 4 Duration (min)"
                type="number"
                value={num(formData.tier_4_duration, 60)}
                onChange={(value) =>
                  updateField("tier_4_duration", Number(value))
                }
                min={1}
                max={240}
              />
            </div>
          </div>
        )}

        <FormField
          id="advanced_mode"
          label="Advanced Mode"
          type="checkbox"
          value={bool(formData.advanced_mode, false)}
          onChange={(value) => updateField("advanced_mode", value)}
          description="Enable advanced configuration options like custom connections and battery sections."
        />

        <div className="form__actions">
          <Button type="submit" variant="primary" loading={isSubmitting}>
            Create Network
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default HubForm;
