/**
 * Click indicator overlay script for screenshot capture.
 *
 * Creates a visual overlay positioned at the target element's bounding box
 * using the popover API for top-layer placement. This avoids clipping issues
 * from parent overflow:hidden.
 *
 * When used with Playwright's element.evaluate(code, arg):
 * - el: The element handle (passed automatically by Playwright)
 * - clickableSelector: The CSS selector passed as the second argument
 */
(el, clickableSelector) => {
  // Focus the element first to update UI state (removes hover from previous)
  if (el.focus) {
    try {
      el.focus();
    } catch (e) {
      // Some elements can't be focused
    }
  }

  // Find the best visual target to highlight
  let target = el;

  // Minimum size for a meaningful indicator
  const minSize = 20;
  const rect = el.getBoundingClientRect();

  // If the element is very small, look for a better parent
  if (rect.width < minSize || rect.height < minSize) {
    const clickableParent = el.closest(clickableSelector);
    if (clickableParent) {
      target = clickableParent;
    }
  }

  // For text fields: find the label.mdc-text-field container
  const mdcTextField = el.closest("label.mdc-text-field");
  if (mdcTextField) {
    target = mdcTextField;
  }

  // For entity picker combo box items: find the combo-box-row or item
  const comboBoxRow = el.closest(".combo-box-row");
  if (comboBoxRow) {
    target = comboBoxRow;
  }

  const comboBoxItem = el.closest("ha-combo-box-item");
  if (comboBoxItem) {
    // Prefer the row container if available
    const row = comboBoxItem.closest(".combo-box-row");
    target = row || comboBoxItem;
  }

  // For entity pickers and list items in dialogs
  const entityListItem = el.closest(
    "ha-list-item, mwc-list-item, md-list-item, " + '[role="listitem"], [role="option"]'
  );
  if (entityListItem) {
    // Check if there's a larger list item container
    const listItemParent = entityListItem.closest("ha-list-item, mwc-list-item, md-list-item, md-item");
    target = listItemParent || entityListItem;
  }

  // Prefer specific HA components for highlighting
  const haListItem = el.closest("ha-list-item");
  if (haListItem) target = haListItem;

  const mdItem = el.closest("md-item");
  if (mdItem) target = mdItem;

  const integrationItem = el.closest("ha-integration-list-item");
  if (integrationItem) target = integrationItem;

  // For role-based items (dropdown options, list items)
  const roleItem = el.closest('[role="listitem"], [role="option"]');
  if (roleItem) {
    // But prefer the HA component wrapper if available
    const haWrapper = roleItem.closest("ha-list-item, md-item, mwc-list-item, .combo-box-row");
    target = haWrapper || roleItem;
  }

  // Get target's bounding box and computed styles
  const targetRect = target.getBoundingClientRect();
  const computedStyle = getComputedStyle(target);
  const borderRadius = computedStyle.borderRadius || "0px";

  // Create overlay container using popover API for top-layer placement
  const overlay = document.createElement("div");
  overlay.id = "click-indicator-overlay";

  // Use popover attribute to put it on the top layer
  overlay.setAttribute("popover", "manual");

  // Style the overlay to match the target element
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

  // Show the popover to put it on top layer
  try {
    overlay.showPopover();
  } catch (e) {
    // Fallback if popover API not supported - still works with high z-index
  }
};
