#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "playwright>=1.40.0",
# ]
# ///
# ruff: noqa: T201
"""Convert SVG files to PNG at various resolutions for Home Assistant brands repository."""

from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright  # type: ignore[import-not-found]


async def render_svg_to_png(
    svg_path: Path,
    output_path: Path,
    width: int,
    height: int,
    *,
    use_dark_mode: bool = False,
) -> None:
    """Render an SVG file to PNG at specified dimensions.

    Args:
        svg_path: Path to the source SVG file
        output_path: Path where the PNG will be saved
        width: Width of the output PNG in pixels
        height: Height of the output PNG in pixels
        use_dark_mode: Whether to use dark color scheme (triggers @media query)

    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        # Set color scheme preference to trigger @media (prefers-color-scheme)
        color_scheme = "dark" if use_dark_mode else "light"
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            color_scheme=color_scheme,  # This triggers the @media query in the SVG
        )
        page = await context.new_page()

        # Read the SVG content
        svg_content = svg_path.read_text(encoding="utf-8")

        # Create HTML that properly scales the SVG
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                html, body {{
                    width: {width}px;
                    height: {height}px;
                    overflow: hidden;
                }}
                svg {{
                    display: block;
                    width: {width}px;
                    height: {height}px;
                }}
            </style>
        </head>
        <body>
            {svg_content}
        </body>
        </html>
        """

        await page.set_content(html)
        await page.wait_for_load_state("networkidle")

        # Take screenshot with transparent background
        await page.screenshot(path=str(output_path), type="png", omit_background=True)

        await browser.close()
        mode = "dark" if use_dark_mode else "light"
        print(f"Created {output_path.name} ({mode} mode)")


async def main() -> None:
    """Generate all PNG versions for Home Assistant brands repository."""
    branding_dir = Path(__file__).parent
    assets_dir = branding_dir.parent

    icon_svg = assets_dir / "icon.svg"
    logo_svg = assets_dir / "logo.svg"

    # LIGHT MODE - Browser will use light color scheme, triggering light mode CSS
    print("\n🌞 Generating light mode files...")

    await render_svg_to_png(icon_svg, branding_dir / "icon.png", 256, 256, use_dark_mode=False)
    await render_svg_to_png(icon_svg, branding_dir / "icon@2x.png", 512, 512, use_dark_mode=False)
    await render_svg_to_png(logo_svg, branding_dir / "logo.png", 1024, 256, use_dark_mode=False)
    await render_svg_to_png(logo_svg, branding_dir / "logo@2x.png", 2048, 512, use_dark_mode=False)

    # DARK MODE - Browser will use dark color scheme, triggering @media (prefers-color-scheme: dark)
    print("\n🌙 Generating dark mode files...")

    await render_svg_to_png(icon_svg, branding_dir / "dark_icon.png", 256, 256, use_dark_mode=True)
    await render_svg_to_png(icon_svg, branding_dir / "dark_icon@2x.png", 512, 512, use_dark_mode=True)
    await render_svg_to_png(logo_svg, branding_dir / "dark_logo.png", 1024, 256, use_dark_mode=True)
    await render_svg_to_png(logo_svg, branding_dir / "dark_logo@2x.png", 2048, 512, use_dark_mode=True)

    print("\n✅ All Home Assistant brands files created successfully!")
    print(f"\n📦 Files saved to: {branding_dir}")
    print("\n  Light Mode (browser color-scheme: light):")
    print("    - icon.png (256x256)")
    print("    - icon@2x.png (512x512)")
    print("    - logo.png (1024x256)")
    print("    - logo@2x.png (2048x512)")
    print("\n  Dark Mode (browser color-scheme: dark, triggers @media):")
    print("    - dark_icon.png (256x256)")
    print("    - dark_icon@2x.png (512x512)")
    print("    - dark_logo.png (1024x256)")
    print("    - dark_logo@2x.png (2048x512)")
    print("\n  ✨ PNGs render exactly as the SVGs do in browsers!")


if __name__ == "__main__":
    asyncio.run(main())
