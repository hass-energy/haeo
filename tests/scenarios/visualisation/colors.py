"""Color mapping for visualization elements.

This module defines consistent color schemes for different element types
in the HAEO energy optimization visualizations.
"""

# Define color palettes
_PHOTOVOLTAICS_PALETTE = [
    "#ff7f0e",  # Orange (primary)
    "#ffbb78",  # Light orange
    "#ff9933",  # Medium orange
    "#ff6600",  # Dark orange
    "#ffcc99",  # Pale orange
]

_BATTERY_PALETTE = [
    "#1f77b4",  # Blue (primary)
    "#aec7e8",  # Light blue
    "#4a90d9",  # Medium blue
    "#0d5a9e",  # Dark blue
    "#c5d9f1",  # Pale blue
]

_GRID_PALETTE = [
    "#2ca02c",  # Green (primary)
    "#98df8a",  # Light green
    "#5cb85c",  # Medium green
    "#1e7b1e",  # Dark green
    "#c7e9c0",  # Pale green
]

_LOAD_PALETTE = [
    "#000000",  # Black (primary)
    "#4a4a4a",  # Dark gray
    "#757575",  # Medium gray
    "#2b2b2b",  # Very dark gray
    "#8b8b8b",  # Light gray
]

_FALLBACK_PALETTE = [
    "#7f7f7f",  # Gray
    "#a0a0a0",  # Light gray
    "#606060",  # Dark gray
    "#909090",  # Medium gray
    "#c0c0c0",  # Very light gray
]

# Element type to color palette mapping
# Multiple element types can share the same palette by referencing the same list
# This defines which types are grouped together for color assignment
ELEMENT_COLOR_PALETTES: dict[str, list[str]] = {
    "photovoltaics": _PHOTOVOLTAICS_PALETTE,
    "battery": _BATTERY_PALETTE,
    "grid": _GRID_PALETTE,
    "load": _LOAD_PALETTE,
    "constant_load": _LOAD_PALETTE,  # Shares palette with load
    "forecast_load": _LOAD_PALETTE,  # Shares palette with load
}

# Fallback color palette for unknown element types
FALLBACK_PALETTE = _FALLBACK_PALETTE


class ColorMapper:
    """Maps element names to colors based on their type and order.

    This class maintains state about which elements have been assigned colors,
    ensuring that multiple elements of the same type get distinct but related colors.
    Elements that share the same color palette (e.g., load, constant_load, forecast_load)
    will share the same color counter.
    """

    def __init__(self) -> None:
        """Initialize the color mapper."""
        # Track counters by palette identity (using id()) so types sharing palettes share counters
        self._palette_counters: dict[int, int] = {}
        self._element_colors: dict[str, str] = {}

    def get_color(self, element_name: str, element_type: str) -> str:
        """Get the color for a specific element.

        Args:
            element_name: The name of the element (e.g., "Photovoltaics Array 1")
            element_type: The type of element (e.g., "photovoltaics", "battery", "load")

        Returns:
            Hex color code for the element

        """
        # Return cached color if already assigned
        if element_name in self._element_colors:
            return self._element_colors[element_name]

        # Get the color palette for this element type
        palette = ELEMENT_COLOR_PALETTES.get(element_type, FALLBACK_PALETTE)

        # Use palette identity as the counter key
        # This automatically groups types that share the same palette list
        palette_id = id(palette)

        # Get the next color index for this palette
        index = self._palette_counters.get(palette_id, 0)
        self._palette_counters[palette_id] = index + 1

        # Cycle through the palette if we have more elements than colors
        color = palette[index % len(palette)]

        # Cache and return the color
        self._element_colors[element_name] = color
        return color
