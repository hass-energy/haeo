import { Routes, Route } from "react-router-dom";
import { FlowProvider } from "./context/FlowContext";
import { ConnectionProvider } from "./context/ConnectionContext";
import FlowPage from "./pages/FlowPage";
import NotFoundPage from "./pages/NotFoundPage";

/**
 * HAEO Configuration App
 *
 * This app is loaded via Home Assistant's external step pattern.
 * URL query parameters determine the flow context:
 * - flow_id: The config flow ID to configure
 * - entry_id: Parent config entry ID (for subentry flows)
 * - subentry_type: Element type being configured (battery, grid, etc.)
 * - subentry_id: Existing subentry ID (for reconfigure flows)
 * - source: Flow source (user, reconfigure)
 * - mode: Flow mode (hub, element, options)
 */
function App() {
  return (
    <ConnectionProvider>
      <FlowProvider>
        <Routes>
          <Route path="/" element={<FlowPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </FlowProvider>
    </ConnectionProvider>
  );
}

export default App;
