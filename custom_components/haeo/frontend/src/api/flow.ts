/**
 * HAEO Flow API for configuring elements via Home Assistant.
 */

import { getConnection, type ConfigEntry } from "./connection";
import type { FlowParams, FlowResult } from "../types";

/**
 * Parse flow parameters from URL query string.
 */
export function parseFlowParams(searchParams: URLSearchParams): FlowParams {
  const flowId = searchParams.get("flow_id");
  if (!flowId) {
    throw new Error("Missing flow_id parameter");
  }

  return {
    flowId,
    entryId: searchParams.get("entry_id") ?? undefined,
    subentryType: searchParams.get("subentry_type") ?? undefined,
    subentryId: searchParams.get("subentry_id") ?? undefined,
    source: (searchParams.get("source") as FlowParams["source"]) ?? undefined,
    mode: (searchParams.get("mode") as FlowParams["mode"]) ?? undefined,
  };
}

/**
 * Submit flow configuration to Home Assistant.
 *
 * @param flowId - The config flow ID
 * @param data - Configuration data to submit
 * @returns Flow result from Home Assistant
 */
export async function submitFlow(
  flowId: string,
  data: Record<string, unknown>
): Promise<FlowResult> {
  const connection = getConnection();
  return connection.sendMessage({
    type: "config_entries/flow",
    flow_id: flowId,
    user_input: data,
  });
}

/**
 * Get the current flow progress/state.
 *
 * @param flowId - The config flow ID
 * @returns Current flow state
 */
export async function getFlowProgress(flowId: string): Promise<FlowResult> {
  const connection = getConnection();
  return connection.sendMessage({
    type: "config_entries/flow/progress",
    flow_id: flowId,
  });
}

/**
 * Abort a config flow.
 *
 * @param flowId - The config flow ID to abort
 */
export async function abortFlow(flowId: string): Promise<void> {
  const connection = getConnection();
  await connection.sendMessage({
    type: "config_entries/flow/abort",
    flow_id: flowId,
  });
}

/**
 * Get HAEO config entries with their subentries.
 *
 * @returns List of HAEO config entries
 */
export async function getHaeoEntries(): Promise<ConfigEntry[]> {
  const connection = getConnection();
  return connection.getConfigEntries();
}

/**
 * Get existing element names from a hub entry.
 * Used for connection dropdown options.
 *
 * @param entryId - The hub config entry ID
 * @param excludeSubentryId - Optional subentry ID to exclude (current element)
 * @returns List of element names that can be used as connection targets
 */
export async function getParticipants(
  entryId: string,
  excludeSubentryId?: string
): Promise<string[]> {
  const connection = getConnection();
  const result = await connection.sendMessage({
    type: "haeo/get_participants",
    entry_id: entryId,
    ...(excludeSubentryId && { exclude_subentry_id: excludeSubentryId }),
  });
  return (result as { participants: string[] }).participants;
}

/**
 * Get subentry data for reconfiguration.
 *
 * @param entryId - The hub config entry ID
 * @param subentryId - The subentry ID to get
 * @returns Subentry data including name, element type, and all config fields
 */
export async function getSubentryData(
  entryId: string,
  subentryId: string
): Promise<Record<string, unknown>> {
  const connection = getConnection();
  const result = await connection.sendMessage({
    type: "haeo/get_subentry",
    entry_id: entryId,
    subentry_id: subentryId,
  });
  return (result as { data: Record<string, unknown> }).data;
}

/**
 * Get all element configurations from a hub entry.
 *
 * @param entryId - The hub config entry ID
 * @returns List of all elements with their type, name, and data
 */
export async function getElementConfig(
  entryId: string
): Promise<
  Array<{
    subentry_id: string;
    subentry_type: string;
    element_type: string;
    name: string;
    data: Record<string, unknown>;
  }>
> {
  const connection = getConnection();
  const result = await connection.sendMessage({
    type: "haeo/get_element_config",
    entry_id: entryId,
  });
  return (
    result as {
      elements: Array<{
        subentry_id: string;
        subentry_type: string;
        element_type: string;
        name: string;
        data: Record<string, unknown>;
      }>;
    }
  ).elements;
}

/**
 * Ping the flow to keep it alive.
 * Flows timeout after ~10 minutes of inactivity.
 *
 * @param flowId - The config flow ID
 * @returns True if flow is still active
 */
export async function pingFlow(flowId: string): Promise<boolean> {
  try {
    await getFlowProgress(flowId);
    return true;
  } catch {
    return false;
  }
}

/**
 * Save flow draft to localStorage.
 *
 * @param flowId - The config flow ID
 * @param data - Draft configuration data
 */
export function saveDraft(
  flowId: string,
  data: Record<string, unknown>
): void {
  const key = `haeo_draft_${flowId}`;
  localStorage.setItem(key, JSON.stringify(data));
}

/**
 * Load flow draft from localStorage.
 *
 * @param flowId - The config flow ID
 * @returns Saved draft or null
 */
export function loadDraft(
  flowId: string
): Record<string, unknown> | null {
  const key = `haeo_draft_${flowId}`;
  const saved = localStorage.getItem(key);
  if (saved) {
    try {
      return JSON.parse(saved) as Record<string, unknown>;
    } catch {
      return null;
    }
  }
  return null;
}

/**
 * Clear flow draft from localStorage.
 *
 * @param flowId - The config flow ID
 */
export function clearDraft(flowId: string): void {
  const key = `haeo_draft_${flowId}`;
  localStorage.removeItem(key);
}
