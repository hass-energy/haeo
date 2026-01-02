/**
 * Main flow page that renders the appropriate form based on flow parameters.
 */

import { useConnection } from "../context/ConnectionContext";
import { useFlow } from "../context/FlowContext";
import Layout from "../components/Layout";
import LoadingSpinner from "../components/LoadingSpinner";
import ConnectionStatus from "../components/ConnectionStatus";
import HubForm from "../components/forms/HubForm";
import ElementForm from "../components/forms/ElementForm";
import FlowExpired from "../components/FlowExpired";
import FlowSuccess from "../components/FlowSuccess";

function FlowPage() {
  const { state, isReady } = useConnection();
  const { params, isActive, result } = useFlow();

  // Show loading while connecting
  if (state === "connecting" || state === "reconnecting") {
    return (
      <Layout>
        <div className="flow-page flow-page--loading">
          <LoadingSpinner message="Connecting to Home Assistant..." />
        </div>
      </Layout>
    );
  }

  // Show error if connection failed
  if (state === "error" || state === "disconnected") {
    return (
      <Layout>
        <div className="flow-page flow-page--error">
          <ConnectionStatus />
        </div>
      </Layout>
    );
  }

  // Show error if no flow params
  if (!params) {
    return (
      <Layout>
        <div className="flow-page flow-page--error">
          <h2>Invalid Flow</h2>
          <p>Missing or invalid flow parameters in URL.</p>
          <p>
            This page should be opened from Home Assistant&apos;s configuration
            flow.
          </p>
        </div>
      </Layout>
    );
  }

  // Show expired message if flow timed out
  if (!isActive) {
    return (
      <Layout>
        <FlowExpired flowId={params.flowId} />
      </Layout>
    );
  }

  // Show success message if flow completed
  if (
    result?.type === "create_entry" ||
    result?.type === "external_step_done"
  ) {
    return (
      <Layout>
        <FlowSuccess result={result} />
      </Layout>
    );
  }

  // Wait for connection to be ready
  if (!isReady) {
    return (
      <Layout>
        <div className="flow-page flow-page--loading">
          <LoadingSpinner message="Loading..." />
        </div>
      </Layout>
    );
  }

  // Render appropriate form based on mode
  return (
    <Layout>
      <div className="flow-page">
        {params.mode === "hub" || !params.mode ? (
          // Hub creation/options flow
          <HubForm />
        ) : (
          // Element creation/edit flow
          <ElementForm />
        )}
      </div>
    </Layout>
  );
}

export default FlowPage;
