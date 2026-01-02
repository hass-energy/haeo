/**
 * Home Assistant WebSocket connection management.
 *
 * Provides auto-reconnect with exponential backoff and wraps
 * the home-assistant-js-websocket API for HAEO-specific calls.
 */

import {
  createConnection,
  createLongLivedTokenAuth,
  getAuth,
  subscribeEntities,
  type Auth,
  type Connection,
  type HassEntities,
  type MessageBase,
} from "home-assistant-js-websocket";

/** Connection state */
export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";

/** Connection state change callback */
export type ConnectionStateCallback = (state: ConnectionState) => void;

/** Entity state change callback */
export type EntitiesCallback = (entities: HassEntities) => void;

/** Reconnect backoff intervals in milliseconds */
const BACKOFF_INTERVALS = [1000, 2000, 4000, 8000, 8000, 8000];

/**
 * Home Assistant WebSocket connection manager.
 */
export class HAConnection {
  private connection: Connection | null = null;
  private auth: Auth | null = null;
  private state: ConnectionState = "disconnected";
  private stateCallbacks: Set<ConnectionStateCallback> = new Set();
  private entitiesCallbacks: Set<EntitiesCallback> = new Set();
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private unsubscribeEntities: (() => void) | null = null;

  /**
   * Connect to Home Assistant.
   *
   * Uses session auth when running in HA context, or a token for development.
   */
  async connect(hassUrl?: string, accessToken?: string): Promise<void> {
    if (this.state === "connected" || this.state === "connecting") {
      return;
    }

    this.setState("connecting");

    try {
      // Get auth - either from HA context or provided token
      if (accessToken) {
        this.auth = createLongLivedTokenAuth(
          hassUrl || window.location.origin,
          accessToken
        );
      } else {
        // Running in HA context - use session auth
        this.auth = await getAuth({
          hassUrl: hassUrl || window.location.origin,
        });
      }

      this.connection = await createConnection({ auth: this.auth });
      this.reconnectAttempt = 0;
      this.setState("connected");

      // Set up disconnect handler for auto-reconnect
      this.connection.addEventListener("disconnected", () => {
        this.handleDisconnect();
      });

      // Subscribe to entity state changes
      this.unsubscribeEntities = subscribeEntities(
        this.connection,
        (entities) => {
          this.entitiesCallbacks.forEach((cb) => cb(entities));
        }
      );
    } catch (error) {
      console.error("Failed to connect to Home Assistant:", error);
      this.setState("error");
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from Home Assistant.
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.unsubscribeEntities) {
      this.unsubscribeEntities();
      this.unsubscribeEntities = null;
    }

    if (this.connection) {
      this.connection.close();
      this.connection = null;
    }

    this.setState("disconnected");
  }

  /**
   * Subscribe to connection state changes.
   */
  onStateChange(callback: ConnectionStateCallback): () => void {
    this.stateCallbacks.add(callback);
    // Immediately call with current state
    callback(this.state);
    return () => this.stateCallbacks.delete(callback);
  }

  /**
   * Subscribe to entity state changes.
   */
  onEntitiesChange(callback: EntitiesCallback): () => void {
    this.entitiesCallbacks.add(callback);
    return () => this.entitiesCallbacks.delete(callback);
  }

  /**
   * Get current connection state.
   */
  getState(): ConnectionState {
    return this.state;
  }

  /**
   * Send a WebSocket message and return the result.
   */
  async sendMessage<T>(message: MessageBase): Promise<T> {
    if (!this.connection) {
      throw new Error("Not connected to Home Assistant");
    }
    return this.connection.sendMessagePromise(message);
  }

  /**
   * Configure a config flow with the given data.
   */
  async configureFlow(
    flowId: string,
    data: Record<string, unknown>
  ): Promise<unknown> {
    return this.sendMessage({
      type: "config_entries/flow",
      flow_id: flowId,
      ...data,
    });
  }

  /**
   * Get the entity registry.
   */
  async getEntityRegistry(): Promise<EntityRegistryEntry[]> {
    return this.sendMessage({
      type: "config/entity_registry/list",
    });
  }

  /**
   * Get the device registry.
   */
  async getDeviceRegistry(): Promise<DeviceRegistryEntry[]> {
    return this.sendMessage({
      type: "config/device_registry/list",
    });
  }

  /**
   * Get config entries for HAEO domain.
   */
  async getConfigEntries(): Promise<ConfigEntry[]> {
    return this.sendMessage({
      type: "config_entries/get",
      domain: "haeo",
    });
  }

  private setState(state: ConnectionState): void {
    this.state = state;
    this.stateCallbacks.forEach((cb) => cb(state));
  }

  private handleDisconnect(): void {
    this.setState("reconnecting");
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    const delay =
      BACKOFF_INTERVALS[
        Math.min(this.reconnectAttempt, BACKOFF_INTERVALS.length - 1)
      ];
    this.reconnectAttempt++;

    console.log(
      `Reconnecting to Home Assistant in ${delay}ms (attempt ${this.reconnectAttempt})`
    );

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }
}

/** Entity registry entry from HA */
export interface EntityRegistryEntry {
  entity_id: string;
  name: string | null;
  original_name: string | null;
  platform: string;
  device_id: string | null;
  area_id: string | null;
  disabled_by: string | null;
  hidden_by: string | null;
  entity_category: string | null;
  icon: string | null;
  unit_of_measurement: string | null;
  device_class: string | null;
}

/** Device registry entry from HA */
export interface DeviceRegistryEntry {
  id: string;
  name: string | null;
  manufacturer: string | null;
  model: string | null;
  area_id: string | null;
}

/** Config entry from HA */
export interface ConfigEntry {
  entry_id: string;
  domain: string;
  title: string;
  source: string;
  state: string;
  supports_options: boolean;
  supports_remove_device: boolean;
  supports_unload: boolean;
  pref_disable_new_entities: boolean;
  pref_disable_polling: boolean;
  disabled_by: string | null;
  reason: string | null;
}

// Singleton instance
let connectionInstance: HAConnection | null = null;

/**
 * Get the singleton connection instance.
 */
export function getConnection(): HAConnection {
  if (!connectionInstance) {
    connectionInstance = new HAConnection();
  }
  return connectionInstance;
}
