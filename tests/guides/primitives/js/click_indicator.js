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

  // Walk up through shadow DOM boundaries to find the closest matching ancestor.
  // Unlike Element.closest(), this crosses shadow root boundaries by jumping
  // from each shadow root to its host element and continuing the search.
  function closestAcrossShadow(node, selector) {
    let current = node;
    while (current) {
      const match = current.closest ? current.closest(selector) : null;
      if (match) return match;
      const root = current.getRootNode();
      if (root === document || !root.host) return null;
      current = root.host;
    }
    return null;
  }

  let target = el;

  // Walk up through shadow DOM to find the nearest clickable ancestor
  const clickableParent = closestAcrossShadow(el, clickableSelector);
  if (clickableParent) target = clickableParent;

  // More specific overrides below — these take priority over the generic match

  const mdcTextField = closestAcrossShadow(el, "label.mdc-text-field");
  if (mdcTextField) target = mdcTextField;

  const comboBoxRow = closestAcrossShadow(el, ".combo-box-row");
  if (comboBoxRow) target = comboBoxRow;

  const comboBoxItem = closestAcrossShadow(el, "ha-combo-box-item");
  if (comboBoxItem) {
    const row = closestAcrossShadow(comboBoxItem, ".combo-box-row");
    target = row || comboBoxItem;
  }

  const entityListItem = closestAcrossShadow(el,
    "ha-list-item, mwc-list-item, md-list-item, " + '[role="listitem"], [role="option"]'
  );
  if (entityListItem) {
    const listItemParent = closestAcrossShadow(entityListItem,
      "ha-list-item, mwc-list-item, md-list-item, md-item"
    );
    target = listItemParent || entityListItem;
  }

  const haListItem = closestAcrossShadow(el, "ha-list-item");
  if (haListItem) target = haListItem;

  const mdItem = closestAcrossShadow(el, "md-item");
  if (mdItem) target = mdItem;

  const integrationItem = closestAcrossShadow(el, "ha-integration-list-item");
  if (integrationItem) target = integrationItem;

  const roleItem = closestAcrossShadow(el, '[role="listitem"], [role="option"]');
  if (roleItem) {
    const haWrapper = closestAcrossShadow(roleItem,
      "ha-list-item, md-item, mwc-list-item, .combo-box-row"
    );
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
