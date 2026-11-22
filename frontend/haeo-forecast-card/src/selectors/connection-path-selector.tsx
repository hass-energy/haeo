import type { JSX } from "preact";

import { ConnectionPathField } from "./ConnectionPathField";
import { HaeoSelectorElement } from "./selector-element";
import type { FieldContext } from "./selector-element";
import type { ConnectionPath, ConnectionPathConfig } from "./types";

/** The selector key the integration's `ConnectionPathSelector` serializes under. */
export const CONNECTION_PATH_SELECTOR_TYPE = "haeo_connection_path";

/** Home Assistant renders a selector of type `haeo_connection_path` as this element. */
export class HaeoConnectionPathSelector extends HaeoSelectorElement<ConnectionPathConfig, ConnectionPath> {
  protected readonly selectorType = CONNECTION_PATH_SELECTOR_TYPE;

  protected renderField(context: FieldContext<ConnectionPathConfig, ConnectionPath>): JSX.Element {
    return <ConnectionPathField {...context} />;
  }
}
