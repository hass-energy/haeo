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
  type AuthData,
  type Connection,
  type HassEntities,
  type MessageBase,
} from "home-assistant-js-websocket";

/** Storage key for auth tokens */
const AUTH_TOKENS_KEY = "hassTokens";

/** Storage key for preserving flow params across auth redirects */
const FLOW_PARAMS_KEY = "haeo_flow_params";

/**
 * Load tokens from localStorage.
 */
async function loadTokens(): Promise<AuthData | null | undefined> {
  try {
    const stored = localStorage.getItem(AUTH_TOKENS_KEY);
    if (stored) {
      return JSON.parse(stored) as AuthData;
    }
  } catch {
    // Ignore parse errors
  }
  return null;
}

/**
 * Save tokens to localStorage.
 */
function saveTokens(data: AuthData | null): void {
  try {
    if (data) {
      localStorage.setItem(AUTH_TOKENS_KEY, JSON.stringify(data));
    } else {
      localStorage.removeItem(AUTH_TOKENS_KEY);
    }
  } catch {
    // Ignore storage errors
  }
}

/**
 * Save current flow parameters before auth redirect.
 * These will be restored after the OAuth callback.
 */
function saveFlowParams(): void {
  const params = window.location.search;
  if (params && params.includes("flow_id")) {
    try {
      sessionStorage.setItem(FLOW_PARAMS_KEY, params);
    } catch {
      // Ignore storage errors
    }
  }
}

/**
 * Restore flow parameters after auth redirect.
 * Redirects to the original URL with flow params if they were saved.
 */
function restoreFlowParams(): boolean {
  try {
    const savedParams = sessionStorage.getItem(FLOW_PARAMS_KEY);
    if (savedParams && !window.location.search.includes("flow_id")) {
      // We have saved params but current URL doesn't have flow_id
      // This means we just returned from auth redirect
      sessionStorage.removeItem(FLOW_PARAMS_KEY);
      const newUrl = window.location.pathname + savedParams;
      window.history.replaceState(null, "", newUrl);
      return true;
    }
  } catch {
    // Ignore storage errors
  }
  return false;
}

// Restore flow params on module load (before React renders)
restoreFlowParams();

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
        // Save flow params before auth - getAuth may redirect to HA's auth page
        saveFlowParams();

        const targetUrl = hassUrl || window.location.origin;
        console.log("Starting auth flow...", {
          hassUrl: targetUrl,
          hasAuthCallback: window.location.search.includes("auth_callback"),
          search: window.location.search,
          existingTokens: localStorage.getItem(AUTH_TOKENS_KEY)?.substring(0, 100),
        });

        // Use explicit loadTokens/saveTokens to ensure token reuse
        this.auth = await getAuth({
          hassUrl: targetUrl,
          loadTokens,
          saveTokens,
        });

        console.log("Auth completed successfully");
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
   * Get the current access token for REST API calls.
   */
  getAccessToken(): string | null {
    return this.auth?.accessToken ?? null;
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
