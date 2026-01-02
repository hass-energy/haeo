/**
 * Connection context for Home Assistant WebSocket connection.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { HassEntities } from "home-assistant-js-websocket";
import {
  getConnection,
  type ConnectionState,
  type EntityRegistryEntry,
  type HAConnection,
} from "../api/connection";

interface ConnectionContextValue {
  /** Current connection state */
  state: ConnectionState;
  /** Home Assistant entities */
  entities: HassEntities;
  /** Entity registry entries */
  entityRegistry: EntityRegistryEntry[];
  /** The connection instance */
  connection: HAConnection;
  /** Whether the connection is ready for use */
  isReady: boolean;
}

const ConnectionContext = createContext<ConnectionContextValue | null>(null);

interface ConnectionProviderProps {
  children: ReactNode;
}

/**
 * Provider for Home Assistant connection state.
 */
export function ConnectionProvider({ children }: ConnectionProviderProps) {
  const [state, setState] = useState<ConnectionState>("disconnected");
  const [entities, setEntities] = useState<HassEntities>({});
  const [entityRegistry, setEntityRegistry] = useState<EntityRegistryEntry[]>(
    []
  );
  const connection = getConnection();

  useEffect(() => {
    // Subscribe to connection state changes
    const unsubState = connection.onStateChange(setState);

    // Subscribe to entity updates
    const unsubEntities = connection.onEntitiesChange(setEntities);

    // Start connection
    connection.connect();

    // Load entity registry when connected
    const loadRegistry = async () => {
      if (connection.getState() === "connected") {
        try {
          const registry = await connection.getEntityRegistry();
          setEntityRegistry(registry);
        } catch (error) {
          console.error("Failed to load entity registry:", error);
        }
      }
    };

    // Load registry immediately if already connected
    loadRegistry();

    // Also load when state changes to connected
    const handleStateChange = (newState: ConnectionState) => {
      if (newState === "connected") {
        loadRegistry();
      }
    };
    const unsubStateForRegistry = connection.onStateChange(handleStateChange);

    return () => {
      unsubState();
      unsubEntities();
      unsubStateForRegistry();
    };
  }, [connection]);

  const value: ConnectionContextValue = {
    state,
    entities,
    entityRegistry,
    connection,
    isReady: state === "connected",
  };

  return (
    <ConnectionContext.Provider value={value}>
      {children}
    </ConnectionContext.Provider>
  );
}

/**
 * Hook to access connection context.
 */
export function useConnection(): ConnectionContextValue {
  const context = useContext(ConnectionContext);
  if (!context) {
    throw new Error("useConnection must be used within a ConnectionProvider");
  }
  return context;
}
