// Configure Mermaid to use theme-aware colors
// This ensures diagrams automatically adapt to light/dark mode
document$.subscribe(() => {
  // Detect current theme
  const palette = __md_get("__palette");
  const scheme = palette && palette.color ? palette.color.scheme : "default";
  const isDark = scheme === "slate";

  // Configure Mermaid theme
  mermaid.initialize({
    startOnLoad: true,
    theme: isDark ? "dark" : "default",
    themeVariables: {
      // These colors work well in both light and dark mode
      // Semantic colors for HAEO diagrams
      primaryColor: isDark ? "#1e88e5" : "#2196f3", // Blue for general elements
      primaryTextColor: isDark ? "#ffffff" : "#000000",
      primaryBorderColor: isDark ? "#64b5f6" : "#1976d2",
      lineColor: isDark ? "#90caf9" : "#1565c0",
      secondaryColor: isDark ? "#43a047" : "#66bb6a", // Green for generation (solar)
      tertiaryColor: isDark ? "#e53935" : "#ef5350", // Red for consumption (loads)
      noteBkgColor: isDark ? "#424242" : "#fff9c4",
      noteTextColor: isDark ? "#ffffff" : "#000000",
      noteBorderColor: isDark ? "#757575" : "#fbc02d",
    },
  });

  // Re-render mermaid diagrams when theme changes
  mermaid.contentLoaded();
});
