import { HaeoInputSelector, INPUT_SELECTOR_TYPE } from "./selectors/input-selector";
import { registerCardElement } from "./register-card-element";

// Home Assistant renders a selector of type X as the element `ha-selector-X`.
registerCardElement(`ha-selector-${INPUT_SELECTOR_TYPE}`, HaeoInputSelector);
