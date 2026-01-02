/**
 * Connection status display component.
 */

import { useConnection } from "../context/ConnectionContext";
import "./ConnectionStatus.css";

function ConnectionStatus() {
  const { state, connection } = useConnection();

  const handleRetry = () => {
    connection.connect();
  };

  return (
    <div className="connection-status">
      <div className={`connection-status__indicator connection-status__indicator--${state}`} />
      <div className="connection-status__content">
        <h3 className="connection-status__title">
          {state === "connected" && "Connected"}
          {state === "connecting" && "Connecting..."}
          {state === "reconnecting" && "Reconnecting..."}
          {state === "disconnected" && "Disconnected"}
          {state === "error" && "Connection Error"}
        </h3>
        <p className="connection-status__message">
          {state === "error" && "Unable to connect to Home Assistant."}
          {state === "disconnected" && "Not connected to Home Assistant."}
          {state === "reconnecting" && "Attempting to reconnect..."}
        </p>
        {(state === "error" || state === "disconnected") && (
          <button
            type="button"
            className="connection-status__retry-btn"
            onClick={handleRetry}
          >
            Retry Connection
          </button>
        )}
      </div>
    </div>
  );
}

export default ConnectionStatus;
