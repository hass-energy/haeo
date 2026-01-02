/**
 * Flow expired message component.
 */

import { loadDraft } from "../api/flow";
import "./FlowExpired.css";

interface FlowExpiredProps {
  flowId: string;
}

function FlowExpired({ flowId }: FlowExpiredProps) {
  const hasDraft = loadDraft(flowId) !== null;

  return (
    <div className="flow-expired">
      <div className="flow-expired__icon" aria-hidden="true">
        ⏰
      </div>
      <h2 className="flow-expired__title">Flow Expired</h2>
      <p className="flow-expired__message">
        The configuration flow has timed out due to inactivity.
      </p>
      {hasDraft && (
        <p className="flow-expired__draft-notice">
          Your draft has been saved. Return to Home Assistant and start a new
          configuration flow to continue where you left off.
        </p>
      )}
      <p className="flow-expired__instructions">
        Please close this window and start a new configuration flow from Home
        Assistant.
      </p>
    </div>
  );
}

export default FlowExpired;
