import { BUFFER_PREVIEW_SELECTOR_TYPE, HaeoBufferPreviewSelector } from "./selectors/buffer-preview-selector";
import { CONNECTION_PATH_SELECTOR_TYPE, HaeoConnectionPathSelector } from "./selectors/connection-path-selector";
import { CONNECTION_SELECTOR_TYPE, HaeoConnectionSelector } from "./selectors/connection-selector";
import { HaeoInputSelector, INPUT_SELECTOR_TYPE } from "./selectors/input-selector";
import { HaeoPolicyRulesSelector, POLICY_RULES_SELECTOR_TYPE } from "./selectors/policy-rules-selector";
import { registerCardElement } from "./register-card-element";

// Home Assistant renders a selector of type X as the element `ha-selector-X`.
registerCardElement(`ha-selector-${INPUT_SELECTOR_TYPE}`, HaeoInputSelector);
registerCardElement(`ha-selector-${CONNECTION_SELECTOR_TYPE}`, HaeoConnectionSelector);
registerCardElement(`ha-selector-${CONNECTION_PATH_SELECTOR_TYPE}`, HaeoConnectionPathSelector);
registerCardElement(`ha-selector-${POLICY_RULES_SELECTOR_TYPE}`, HaeoPolicyRulesSelector);
registerCardElement(`ha-selector-${BUFFER_PREVIEW_SELECTOR_TYPE}`, HaeoBufferPreviewSelector);
