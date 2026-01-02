/**
 * Element configuration form - renders the appropriate form based on element type.
 */

import { useFlow } from "../../context/FlowContext";
import Card from "../ui/Card";
import BatteryForm from "./BatteryForm";
import GridForm from "./GridForm";
import SolarForm from "./SolarForm";
import LoadForm from "./LoadForm";
import NodeForm from "./NodeForm";
import InverterForm from "./InverterForm";
import ConnectionForm from "./ConnectionForm";
import "./Form.css";

function ElementForm() {
  const { params } = useFlow();

  if (!params?.subentryType) {
    return (
      <Card>
        <div className="form">
          <h2 className="form__title">Unknown Element Type</h2>
          <p>No element type specified in flow parameters.</p>
        </div>
      </Card>
    );
  }

  // Render form based on element type
  switch (params.subentryType) {
    case "battery":
      return <BatteryForm />;
    case "grid":
      return <GridForm />;
    case "solar":
      return <SolarForm />;
    case "load":
      return <LoadForm />;
    case "node":
      return <NodeForm />;
    case "inverter":
      return <InverterForm />;
    case "connection":
      return <ConnectionForm />;
    default:
      return (
        <Card>
          <div className="form">
            <h2 className="form__title">Unsupported Element</h2>
            <p>
              Element type &quot;{params.subentryType}&quot; is not yet
              supported in this interface.
            </p>
          </div>
        </Card>
      );
  }
}

export default ElementForm;
