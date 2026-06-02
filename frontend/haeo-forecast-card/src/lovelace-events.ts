/**
 * Dispatch Home Assistant's Lovelace layout refresh event from a custom card.
 *
 * Use the host document's Event constructor so Node/jsdom scenario exports accept
 * the dispatched event (global `Event` is a different class in jsdom).
 */
export function dispatchLovelaceUpdate(host: HTMLElement): void {
  const EventCtor = host.ownerDocument.defaultView?.Event ?? Event;
  host.dispatchEvent(new EventCtor("ll-update", { bubbles: true, composed: true }));
}
