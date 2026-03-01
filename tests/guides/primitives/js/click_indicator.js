/**
 * Click indicator overlay script for screenshot capture.
 *
 * Creates a visual overlay positioned at the target element's bounding box
 * using the popover API for top-layer placement. This avoids clipping issues
 * from parent overflow:hidden.
 */
(el, clickableSelector) => {
  if (el.focus) {
    try {
      el.focus();
    } catch (e) {}
  }

  let target = el;
  const minSize = 20;
  const rect = el.getBoundingClientRect();

  if (rect.width < minSize || rect.height < minSize) {
    const clickableParent = el.closest(clickableSelector);
    if (clickableParent) target = clickableParent;
  }

  const mdcTextField = el.closest("label.mdc-text-field");
  if (mdcTextField) target = mdcTextField;

  const comboBoxRow = el.closest(".combo-box-row");
  if (comboBoxRow) target = comboBoxRow;

  const comboBoxItem = el.closest("ha-combo-box-item");
  if (comboBoxItem) {
    const row = comboBoxItem.closest(".combo-box-row");
    target = row || comboBoxItem;
  }

  const entityListItem = el.closest(
    "ha-list-item, mwc-list-item, md-list-item, " + '[role="listitem"], [role="option"]'
  );
  if (entityListItem) {
    const listItemParent = entityListItem.closest("ha-list-item, mwc-list-item, md-list-item, md-item");
    target = listItemParent || entityListItem;
  }

  const haListItem = el.closest("ha-list-item");
  if (haListItem) target = haListItem;

  const mdItem = el.closest("md-item");
  if (mdItem) target = mdItem;

  const integrationItem = el.closest("ha-integration-list-item");
  if (integrationItem) target = integrationItem;

  const roleItem = el.closest('[role="listitem"], [role="option"]');
  if (roleItem) {
    const haWrapper = roleItem.closest("ha-list-item, md-item, mwc-list-item, .combo-box-row");
    target = haWrapper || roleItem;
  }

  const targetRect = target.getBoundingClientRect();
  const computedStyle = getComputedStyle(target);
  const borderRadius = computedStyle.borderRadius || "0px";

  const overlay = document.createElement("div");
  overlay.id = "click-indicator-overlay";
  overlay.setAttribute("popover", "manual");
  overlay.style.cssText = `
    position: fixed;
    left: ${targetRect.left - 3}px;
    top: ${targetRect.top - 3}px;
    width: ${targetRect.width + 6}px;
    height: ${targetRect.height + 6}px;
    border: 3px solid rgba(255, 0, 0, 0.9);
    border-radius: ${borderRadius};
    box-shadow: 0 0 15px 5px rgba(255, 0, 0, 0.4);
    pointer-events: none;
    z-index: 2147483647;
    margin: 0;
    padding: 0;
    background: transparent;
    box-sizing: border-box;
  `;
  document.body.appendChild(overlay);
  try {
    overlay.showPopover();
  } catch (e) {}
};
