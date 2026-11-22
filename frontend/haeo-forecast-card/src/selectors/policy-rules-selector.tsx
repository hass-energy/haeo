import type { JSX } from "preact";

import { PolicyRulesField } from "./PolicyRulesField";
import { HaeoSelectorElement } from "./selector-element";
import type { FieldContext } from "./selector-element";
import type { PolicyRule, PolicyRulesConfig } from "./types";

/** The selector key the integration's `PolicyRulesSelector` serializes under. */
export const POLICY_RULES_SELECTOR_TYPE = "haeo_policy_rules";

/** Home Assistant renders a selector of type `haeo_policy_rules` as this element. */
export class HaeoPolicyRulesSelector extends HaeoSelectorElement<PolicyRulesConfig, PolicyRule[]> {
  protected readonly selectorType = POLICY_RULES_SELECTOR_TYPE;

  protected renderField(context: FieldContext<PolicyRulesConfig, PolicyRule[]>): JSX.Element {
    return <PolicyRulesField {...context} />;
  }
}
