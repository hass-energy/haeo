/**
 * Flow success message component.
 */

import type { FlowResult } from "../types";
import "./FlowSuccess.css";

interface FlowSuccessProps {
  result: FlowResult;
}

function FlowSuccess({ result }: FlowSuccessProps) {
  const title = result.result?.title || "Configuration";

  return (
    <div className="flow-success">
      <div className="flow-success__icon" aria-hidden="true">
        ✓
      </div>
      <h2 className="flow-success__title">Success!</h2>
      <p className="flow-success__message">
        <strong>{title}</strong> has been configured successfully.
      </p>
      <p className="flow-success__instructions">
        This window will close automatically. If it doesn&apos;t, you can close
        it manually.
      </p>
    </div>
  );
}

export default FlowSuccess;
