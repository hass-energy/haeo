/**
 * Node configuration form.
 */

import { useFlow } from "../../context/FlowContext";
import FormField from "./FormField";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { str } from "./utils";
import "./Form.css";

function NodeForm() {
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
          {isReconfigure ? "Edit Node" : "Add Node"}
        </h2>
        <p className="form__description">
          Nodes are junction points in your energy network where power flows
          converge. Power balance is enforced at each node.
        </p>

        {error && (
          <div className="form__error" role="alert">
            {error}
          </div>
        )}

        <FormField
          id="name"
          label="Node Name"
          required
          value={str(formData.name)}
          onChange={(value) => updateField("name", value)}
          placeholder="e.g., Main Bus"
          disabled={isReconfigure}
        />

        <p className="form__description" style={{ marginTop: "1rem" }}>
          After creating this node, you can connect elements (batteries, solar,
          loads, grid) to it.
        </p>

        <div className="form__actions">
          <Button type="submit" variant="primary" loading={isSubmitting}>
            {isReconfigure ? "Save Changes" : "Add Node"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default NodeForm;
