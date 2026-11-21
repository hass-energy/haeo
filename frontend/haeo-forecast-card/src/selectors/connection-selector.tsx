import type { JSX } from "preact";

import { ConnectionField } from "./ConnectionField";
import { HaeoSelectorElement } from "./selector-element";
import type { FieldContext } from "./selector-element";
import type { ConnectionSelectorConfig } from "./types";

/** The selector key the integration's `ConnectionSelector` serializes under. */
export const CONNECTION_SELECTOR_TYPE = "haeo_connection";

/** Home Assistant renders a selector of type `haeo_connection` as this element. */
export class HaeoConnectionSelector extends HaeoSelectorElement<ConnectionSelectorConfig, string> {
  protected readonly selectorType = CONNECTION_SELECTOR_TYPE;

  protected renderField(context: FieldContext<ConnectionSelectorConfig, string>): JSX.Element {
    return <ConnectionField {...context} />;
  }
}
