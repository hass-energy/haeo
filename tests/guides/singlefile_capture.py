"""SingleFile page capture via JavaScript fetch and eval.

This module provides HTML snapshot capture by having JavaScript fetch
the SingleFile bundle from Home Assistant's static file server and
evaluate it directly. This avoids any Python string escaping issues.

The approach:
1. Copy the bundle to config/www/ (served at /local/)
2. Use page.evaluate() to fetch the bundle as text
3. Extract and eval the script content in JavaScript
4. Call singlefile.getPageData() to capture the page

This captures the current authenticated page state, unlike the CLI
which opens a new tab without session cookies.
"""

from __future__ import annotations

import logging
from pathlib import Path
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


def capture_html(page: Page, path: Path, *, timeout: int = 30000) -> bool:
    """Capture the current page as a self-contained HTML file.

    This loads SingleFile by fetching and evaluating the bundle, then
    calls getPageData() to serialize the DOM with all resources inlined.

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
            path.write_text(html_content)
            return True
        _LOGGER.warning("SingleFile returned empty content")
        return False

    except Exception as e:
        _LOGGER.warning("Failed to capture HTML snapshot: %s", e)
        return False
