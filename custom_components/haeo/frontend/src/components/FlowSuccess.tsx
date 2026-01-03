/**
 * Flow success message component.
 */

import { useEffect } from "react";
import type { FlowResult } from "../types";
import "./FlowSuccess.css";

interface FlowSuccessProps {
  result: FlowResult;
}

function FlowSuccess({ result }: FlowSuccessProps) {
  const title = result.result?.title || "Configuration";

  // Redirect back to HA after a short delay
  useEffect(() => {
    const timer = setTimeout(() => {
      // Close window if opened as popup, otherwise redirect to integrations
      if (window.opener) {
        window.close();
      } else {
        window.location.href = "/config/integrations/integration/haeo";
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, []);

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
        Redirecting back to Home Assistant...
      </p>
    </div>
  );
}

export default FlowSuccess;
