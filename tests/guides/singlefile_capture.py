"""SingleFile page capture via JavaScript fetch and eval.

This module provides HTML snapshot capture by having JavaScript fetch
the SingleFile bundle from Home Assistant's static file server and
evaluate it directly. This avoids any Python string escaping issues.

The approach:
1. Copy the bundle to config/www/ (served at /local/)
2. Use page.evaluate() to fetch the bundle as text
3. Extract and eval the script content in JavaScript
4. Pre-process DOM to handle popovers and menus
5. Call singlefile.getPageData() to capture the page
6. Post-process to strip interactive attributes (href, onclick, etc.)

This captures the current authenticated page state, unlike the CLI
which opens a new tab without session cookies.

DOM Pre-processing:
- Fixes MDC dropdown menus (ha-select with mwc-menu-surface)
- Fixes ha-dialog elements that are open
- Fixes popover elements (native Popover API doesn't serialize state)
- Inlines computed positions for absolute/fixed elements using CSS custom properties
- Adds CSS to hide number input spin buttons for static display
"""

from __future__ import annotations

import logging
from pathlib import Path
import re
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

_LOGGER = logging.getLogger(__name__)

# Path to SingleFile bundle in node_modules
_BUNDLE_PATH = (
    Path(__file__).parent.parent.parent / "node_modules" / "single-file-cli" / "lib" / "single-file-bundle.js"
)

# Where to serve the bundle from in Home Assistant
_HA_WWW_PATH = Path(__file__).parent.parent.parent / "config" / "www"
_HA_BUNDLE_NAME = "single-file-bundle.js"
_HA_BUNDLE_URL = f"/local/{_HA_BUNDLE_NAME}"

# CSS rules to inject for static display
_STATIC_DISPLAY_CSS = """
/* Hide number input spin buttons for static display */
input::-webkit-inner-spin-button,
input::-webkit-outer-spin-button {
    -webkit-appearance: none !important;
    appearance: none !important;
    margin: 0 !important;
}
input[type="number"] {
    -moz-appearance: textfield !important;
    appearance: textfield !important;
}
"""

# Regex patterns to strip interactive attributes from HTML
# These patterns match attributes that would make the HTML interactive
_INTERACTIVE_ATTR_PATTERNS = [
    # href attributes on links (keep other attrs)
    re.compile(r'\s+href="[^"]*"', re.IGNORECASE),
    re.compile(r"\s+href='[^']*'", re.IGNORECASE),
    # Event handlers
    re.compile(r'\s+on\w+="[^"]*"', re.IGNORECASE),
    re.compile(r"\s+on\w+='[^']*'", re.IGNORECASE),
    # Form actions
    re.compile(r'\s+action="[^"]*"', re.IGNORECASE),
    re.compile(r"\s+action='[^']*'", re.IGNORECASE),
    # Form methods
    re.compile(r'\s+method="[^"]*"', re.IGNORECASE),
    re.compile(r"\s+method='[^']*'", re.IGNORECASE),
    # Contenteditable
    re.compile(r'\s+contenteditable="[^"]*"', re.IGNORECASE),
    re.compile(r"\s+contenteditable='[^']*'", re.IGNORECASE),
    re.compile(r"\s+contenteditable(?=[>\s])", re.IGNORECASE),
    # Draggable
    re.compile(r'\s+draggable="[^"]*"', re.IGNORECASE),
    re.compile(r"\s+draggable='[^']*'", re.IGNORECASE),
    # Tabindex (prevents keyboard navigation)
    re.compile(r'\s+tabindex="[^"]*"', re.IGNORECASE),
    re.compile(r"\s+tabindex='[^']*'", re.IGNORECASE),
]


def _sanitize_html(html: str) -> str:
    """Remove interactive attributes from HTML to make it a static snapshot.

    This strips href, onclick, and other attributes that would make
    the captured HTML behave interactively when viewed in a browser.

    Args:
        html: The raw HTML content.

    Returns:
        Sanitized HTML with interactive attributes removed.

    """
    for pattern in _INTERACTIVE_ATTR_PATTERNS:
        html = pattern.sub("", html)
    return html


def _ensure_bundle_available() -> bool:
    """Ensure the SingleFile bundle is available in HA's www directory.

    Returns:
        True if bundle is available, False otherwise.

    """
    if not _BUNDLE_PATH.exists():
        _LOGGER.warning(
            "SingleFile bundle not found at %s. Run 'npm install' to install dependencies.",
            _BUNDLE_PATH,
        )
        return False

    # Create www directory if needed
    _HA_WWW_PATH.mkdir(parents=True, exist_ok=True)

    # Copy bundle to www directory
    dest_path = _HA_WWW_PATH / _HA_BUNDLE_NAME
    if not dest_path.exists() or dest_path.stat().st_mtime < _BUNDLE_PATH.stat().st_mtime:
        shutil.copy2(_BUNDLE_PATH, dest_path)
        _LOGGER.debug("Copied SingleFile bundle to %s", dest_path)

    return True


def _inject_singlefile(page: Page) -> bool:
    """Inject SingleFile into the page by fetching and evaluating the bundle.

    This fetches the bundle from HA's static file server, extracts the
    script content from the ES module export, and evals it directly in
    JavaScript - avoiding all Python escaping issues.

    Args:
        page: The Playwright page to inject into.

    Returns:
        True if SingleFile is available, False otherwise.

    """
    # Check if already loaded
    is_available = page.evaluate("typeof singlefile !== 'undefined'")
    if is_available:
        return True

    # Fetch bundle and eval the script content in JavaScript
    result = page.evaluate(
        """async (bundleUrl) => {
            try {
                // Fetch the bundle file
                const response = await fetch(bundleUrl);
                if (!response.ok) {
                    return { error: `Failed to fetch bundle: ${response.status}` };
                }
                const bundleText = await response.text();

                // Extract the script content from the ES module
                // Format: const script = "var singlefile=...";const hookScript
                const startMarker = 'const script = "';
                const endMarker = '";const hookScript';

                const startIdx = bundleText.indexOf(startMarker);
                if (startIdx === -1) {
                    return { error: 'Could not find script start marker' };
                }

                const contentStart = startIdx + startMarker.length;
                const endIdx = bundleText.indexOf(endMarker, contentStart);
                if (endIdx === -1) {
                    return { error: 'Could not find script end marker' };
                }

                // Extract the escaped content and unescape it using JSON.parse
                // The content is a valid JS string literal, so wrapping in quotes
                // and parsing as JSON will properly unescape it
                const escapedContent = bundleText.substring(contentStart, endIdx);
                const scriptContent = JSON.parse('"' + escapedContent + '"');

                // Evaluate the script - this creates a local 'singlefile' variable
                eval(scriptContent);

                // Assign to window so it persists across evaluate() calls
                if (typeof singlefile !== 'undefined') {
                    window.singlefile = singlefile;
                }

                return { success: typeof window.singlefile !== 'undefined' };
            } catch (e) {
                return { error: e.message || String(e) };
            }
        }""",
        _HA_BUNDLE_URL,
    )

    if result.get("error"):
        _LOGGER.warning("Failed to inject SingleFile: %s", result["error"])
        return False

    return result.get("success", False)


def _preprocess_dom(page: Page, static_css: str) -> dict[str, int]:
    """Pre-process DOM to fix elements that don't serialize correctly.

    This handles:
    - MDC dropdown menus (ha-select with mwc-menu-surface hidden attribute)
    - ha-dialog elements that are open but may not serialize
    - Native Popover API elements that show display:none when serialized
    - Menu/popover position values that use CSS custom properties
    - Injecting CSS for static display (hiding spin buttons, etc.)

    Home Assistant uses Material Design Components (MDC) for dropdowns.
    When a dropdown is open, the mwc-menu-surface element should have its
    'hidden' attribute removed and visibility forced. We detect open menus
    by checking their computed visibility and dimensions.

    The Native Popover API renders popovers in the browser's "top layer",
    which is outside the normal DOM. When serializing, these elements
    appear with display:none. We detect open popovers using :popover-open
    and convert them to regular visible divs.

    Args:
        page: The Playwright page to modify.
        static_css: CSS rules to inject for static display.

    Returns:
        Dict with counts of elements fixed.

    """
    return page.evaluate(
        """(staticCss) => {
            const stats = { popoversFixed: 0, positionsFixed: 0, cssInjected: 0, mdcMenusFixed: 0, dialogsFixed: 0 };

            // Inject static display CSS
            if (staticCss) {
                const style = document.createElement('style');
                style.id = 'singlefile-static-css';
                style.textContent = staticCss;
                document.head.appendChild(style);
                stats.cssInjected = 1;
            }

            // Helper to traverse all shadow roots
            function walkShadowRoots(root, callback) {
                callback(root);
                root.querySelectorAll('*').forEach(el => {
                    if (el.shadowRoot) {
                        walkShadowRoots(el.shadowRoot, callback);
                    }
                });
            }

// Fix MDC dropdown menus (ha-select, ha-menu)
            // These use mwc-menu-surface with a 'hidden' attribute that needs
            // to be removed and visibility forced for open dropdowns.
            // We detect open dropdowns by checking if the menu surface is visible.
            walkShadowRoots(document, (root) => {
                root.querySelectorAll('mwc-menu-surface').forEach(menuSurface => {
                    const computed = getComputedStyle(menuSurface);
                    const rect = menuSurface.getBoundingClientRect();

                    // A menu is "open" if it's visible and has dimensions
                    const isVisible = computed.display !== 'none' &&
                                      rect.width > 0 && rect.height > 0;
                    const hasHidden = menuSurface.hasAttribute('hidden');

                    if (isVisible || (!hasHidden && rect.width > 0)) {
                        if (hasHidden) {
                            menuSurface.removeAttribute('hidden');
                        }

                        // Fix inner shadow root surface
                        if (menuSurface.shadowRoot) {
                            const innerSurface = menuSurface.shadowRoot.querySelector('.mdc-menu-surface');
                            if (innerSurface) {
                                innerSurface.classList.add('mdc-menu-surface--open');
                                innerSurface.style.display = 'inline-block';
                                innerSurface.style.opacity = '1';
                                innerSurface.style.transform = 'scale(1)';
                            }
                        }

                        menuSurface.style.display = 'inline-block';

                        if (rect.top !== 0 || rect.left !== 0) {
                            menuSurface.style.position = 'fixed';
                            menuSurface.style.top = rect.top + 'px';
                            menuSurface.style.left = rect.left + 'px';
                            menuSurface.style.zIndex = '9999';
                        }

                        stats.mdcMenusFixed++;
                    }
                });
            });

            // Fix ha-dialog elements that are open
            walkShadowRoots(document, (root) => {
                root.querySelectorAll('ha-dialog, dialog[open]').forEach(dialog => {
                    const computed = getComputedStyle(dialog);
                    const rect = dialog.getBoundingClientRect();

                    if (rect.width > 0 && rect.height > 0 && computed.display !== 'none') {
                        dialog.style.display = 'block';
                        dialog.style.visibility = 'visible';
                        dialog.style.opacity = '1';

                        if (computed.position === 'fixed' || computed.position === 'absolute') {
                            dialog.style.position = 'fixed';
                            dialog.style.top = rect.top + 'px';
                            dialog.style.left = rect.left + 'px';
                            dialog.style.width = rect.width + 'px';
                            dialog.style.height = rect.height + 'px';
                            dialog.style.zIndex = '9999';
                        }

                        stats.dialogsFixed++;
                    }
                });
            });

            // Fix popover elements - the Native Popover API renders them in
            // the browser's "top layer" which doesn't serialize properly.
            // We use :popover-open to detect which popovers are currently shown.
            walkShadowRoots(document, (root) => {
                root.querySelectorAll('[popover]').forEach(el => {
                    try {
                        // Check if this popover is currently open/shown
                        // The :popover-open pseudo-class indicates browser is showing it
                        if (el.matches(':popover-open')) {
                            // Capture computed position before we modify anything
                            const computed = getComputedStyle(el);
                            const rect = el.getBoundingClientRect();

                            // Remove popover attribute so it becomes a normal element
                            el.removeAttribute('popover');

                            // Force visibility and display
                            el.style.display = 'block';
                            el.style.visibility = 'visible';
                            el.style.opacity = '1';

                            // If it was positioned by the popover API, inline the position
                            // Popovers in top-layer use position:fixed relative to viewport
                            if (computed.position === 'fixed' || computed.position === 'absolute') {
                                el.style.position = 'fixed';
                                el.style.top = rect.top + 'px';
                                el.style.left = rect.left + 'px';
                                el.style.width = rect.width + 'px';
                                el.style.zIndex = '9999';
                            }

                            stats.popoversFixed++;
                        }
                    } catch (e) {
                        // :popover-open may not be supported in all contexts
                    }
                });

                // For absolute/fixed elements, inline computed positions
                // CSS custom properties may not serialize correctly
                root.querySelectorAll('.menu, [role="menu"], [role="listbox"]').forEach(el => {
                    const computed = getComputedStyle(el);
                    const position = computed.position;

                    if ((position === 'absolute' || position === 'fixed') &&
                        computed.display !== 'none') {
                        const rect = el.getBoundingClientRect();
                        // Only inline if we have valid positions
                        if (rect.top !== 0 || rect.left !== 0) {
                            if (!el.style.top) el.style.top = rect.top + 'px';
                            if (!el.style.left) el.style.left = rect.left + 'px';
                            stats.positionsFixed++;
                        }
                    }
                });
            });

            return stats;
        }""",
        static_css,
    )


def capture_html(page: Page, path: Path, *, timeout: int = 30000) -> bool:
    """Capture the current page as a self-contained HTML file.

    This loads SingleFile by fetching and evaluating the bundle, then
    calls getPageData() to serialize the DOM with all resources inlined.

    Pre-processing fixes:
    - MDC dropdown menus (ha-select with mwc-menu-surface)
    - ha-dialog elements that are open
    - Native Popover API elements that show display:none when serialized
    - Menu/popover position values using CSS custom properties
    - Injects CSS to hide number input spin buttons

    Args:
        page: The Playwright page to capture
        path: Path where the HTML file should be saved
        timeout: Maximum time in milliseconds to wait for capture

    Returns:
        True if capture succeeded, False otherwise

    """
    # Ensure bundle is available in HA's www directory
    if not _ensure_bundle_available():
        return False

    try:
        # Set page timeout for the operations
        page.set_default_timeout(timeout)

        # Pre-process DOM to fix popovers, menus, and inject static CSS
        _preprocess_dom(page, _STATIC_DISPLAY_CSS)

        # Inject SingleFile
        if not _inject_singlefile(page):
            _LOGGER.warning("Failed to inject SingleFile script")
            return False

        # Capture page data
        html_content = page.evaluate(
            """async () => {
                if (typeof singlefile === 'undefined') {
                    console.error('SingleFile not available');
                    return null;
                }

                // Capture page data with options for static HTML
                const options = {
                    removeHiddenElements: false,
                    removeUnusedStyles: true,
                    removeUnusedFonts: true,
                    removeFrames: true,
                    removeImports: true,
                    removeScripts: true,
                    compressHTML: false,
                    compressCSS: false,
                    loadDeferredImages: false,
                    loadDeferredImagesMaxIdleTime: 0,
                    filenameTemplate: "{page-title}",
                    infobarContent: "",
                    includeInfobar: false,
                    blockScripts: true,
                    blockVideos: false,
                    blockAudios: false,
                    url: window.location.href
                };

                try {
                    const pageData = await singlefile.getPageData(options);
                    return pageData.content;
                } catch (e) {
                    console.error('SingleFile capture error:', e);
                    return null;
                }
            }"""
        )

        if html_content:
            # Sanitize to remove interactive attributes
            html_content = _sanitize_html(html_content)
            path.write_text(html_content)
            return True
        _LOGGER.warning("SingleFile returned empty content")
        return False

    except Exception as e:
        _LOGGER.warning("Failed to capture HTML snapshot: %s", e)
        return False
