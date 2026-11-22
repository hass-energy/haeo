import type { JSX } from "preact";

import { BufferPreviewField } from "./BufferPreviewField";
import { HaeoSelectorElement } from "./selector-element";
import type { FieldContext } from "./selector-element";

/** The selector key the integration's `BufferPreviewSelector` serializes under. */
export const BUFFER_PREVIEW_SELECTOR_TYPE = "haeo_buffer_preview";

interface BufferPreviewConfig {
  entry_id: string;
  replaces: string | null;
}

/**
 * Return the values of the outermost form around an element, crossing shadow roots.
 *
 * A selector is only given its own value, so the preview reads the rest of the
 * buffer's form from Home Assistant's form element, whose `data` holds them all.
 */
export function formData(start: Node): Record<string, unknown> | null {
  let found: Record<string, unknown> | null = null;
  let node: Node | null = start;
  while (node !== null) {
    if (node instanceof HTMLElement && node.localName === "ha-form" && "data" in node) {
      const data = (node as HTMLElement & { data: unknown }).data;
      if (data !== null && typeof data === "object") {
        found = data as Record<string, unknown>;
      }
    }
    node = node.parentNode ?? (node instanceof ShadowRoot ? node.host : null);
  }
  return found;
}

/** Home Assistant renders a selector of type `haeo_buffer_preview` as this element. */
export class HaeoBufferPreviewSelector extends HaeoSelectorElement<BufferPreviewConfig, null> {
  protected readonly selectorType = BUFFER_PREVIEW_SELECTOR_TYPE;

  protected renderField(context: FieldContext<BufferPreviewConfig, null>): JSX.Element {
    return (
      <div class="field">
        <div class="label">{context.label}</div>
        <BufferPreviewField
          hass={context.hass}
          entryId={context.config.entry_id}
          replaces={context.config.replaces}
          readForm={() => formData(this)}
          t={context.t}
        />
      </div>
    );
  }
}
