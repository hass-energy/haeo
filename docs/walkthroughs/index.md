# Walkthroughs

Step-by-step guides for configuring common HAEO setups.
Each walkthrough walks through a complete configuration from start to finish, with interactive screenshot slideshows that show exactly what to click and fill in at every step.
Where it helps, a walkthrough also shows the plan HAEO makes on its own forecast card, so you can see what each change does.

Walkthroughs are generated from a live Home Assistant instance, so the screenshots and plans always reflect the current version of HAEO.

## Available walkthroughs

<div class="grid cards" markdown>

- :material-battery-charging:{ .lg .middle } **Sigenergy System**

    ---

    Complete hybrid inverter setup with battery, solar, grid, and house load.
    Covers a full Sigenergy system with multiple solar arrays, DC/AC coupling, and grid connection.

    [:material-arrow-right: Sigenergy walkthrough](sigenergy-system.md)

- :material-shield-check:{ .lg .middle } **Power Policies**

    ---

    Control how energy flows between elements using source-to-target pricing.
    Covers solar export, battery discharge, and grid charging policies.

    [:material-arrow-right: Power Policies walkthrough](power-policies.md)

- :material-battery-lock:{ .lg .middle } **Reserve and Headroom**

    ---

    Keep energy in your batteries for a grid outage, and room for the solar that is coming.
    Shows the plan changing on the forecast card at every step.

    [:material-arrow-right: Reserve and Headroom walkthrough](reserve-and-headroom.md)

- :material-history:{ .lg .middle } **Historic Diagnostics**

    ---

    Generate a diagnostics snapshot from a past point in time using Developer Tools.
    Useful for reproducing issues and sharing system context with a developer.

    [:material-arrow-right: Historic Diagnostics walkthrough](historic-diagnostics.md)

</div>

## Next steps

<div class="grid cards" markdown>

- :material-cog:{ .lg .middle } **Configuration reference**

    ---

    Detailed reference for hub configuration, the planning horizon, and raw model elements.

    [:material-arrow-right: Configuration guide](../user-guide/configuration.md)

- :material-puzzle:{ .lg .middle } **Element guides**

    ---

    In-depth documentation for each element type and its configuration options.

    [:material-arrow-right: Element documentation](../user-guide/elements/index.md)

- :material-chart-line:{ .lg .middle } **Forecasts and sensors**

    ---

    How HAEO loads forecast and sensor data for optimization.

    [:material-arrow-right: Forecasts guide](../user-guide/forecasts-and-sensors.md)

</div>
