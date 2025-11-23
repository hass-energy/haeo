# [Element Name] Modeling

Brief description of the element's role in the optimization problem (1-2 sentences).
Focus on what decisions the model makes regarding this element.

## Model Formulation

This section describes the mathematical optimization model for this element.
Present the formulation in standard optimization notation.

### Parameters

List all parameters (inputs) required by this element's model.
Distinguish between user-configured parameters and sensor-derived data.

| Parameter        | Dimensions | Source        | Description                           |
| ---------------- | ---------- | ------------- | ------------------------------------- |
| $p_{\text{max}}$ | scalar     | Configuration | Maximum power capacity                |
| $f_{t}$          | $T$        | Sensor        | Forecasted values at each time period |

### Decision Variables

List all decision variables this element introduces to the optimization problem.
Use consistent mathematical notation.

| Variable | Dimensions | Domain                | Description                                  |
| -------- | ---------- | --------------------- | -------------------------------------------- |
| $x_{t}$  | $T$        | $\mathbb{R}_{\geq 0}$ | Description of what this variable represents |
| $y_{t}$  | $T$        | $\{0, 1\}$            | Binary decision variable description         |

### Constraints

List all constraints this element contributes to the optimization problem.
Present each constraint with its mathematical formulation and a brief explanation.

#### Constraint Name

$$
\text{mathematical formulation}
$$

Brief explanation of what this constraint ensures and why it's necessary.

### Cost Contribution

Describe this element's contribution to the objective function.
Explain the economic interpretation.

$$
\text{Cost} = \sum_{t \in T} c_t \cdot x_t
$$

Where $c_t$ represents the cost coefficient at time $t$.

## Physical Interpretation

Provide a conceptual explanation of how the mathematical model relates to real-world behavior.
Focus on intuition, not detailed calculations.

### Example Scenarios

Describe typical operating scenarios and how the model captures them:

**Scenario Name**: Brief description of the scenario and how the model responds.

### Model Assumptions

List key assumptions made in the formulation:

- Assumption one and its implications
- Assumption two and its implications

### Limitations

Note any real-world behaviors not captured by the model:

- Limitation one and when it matters
- Limitation two and potential workarounds

## Related Documentation

!!! note "Template Instructions"

    When using this template:

    1. Replace the element configuration link with the actual element page (e.g., `battery.md`)
    2. Replace `element.py` in the source code link with the actual model filename (e.g., `battery.py`)
    3. Curate Next Steps cards to show 3-4 most relevant actions for readers of this page
    4. Choose cards that flow naturally from this element's modeling concepts

<div class="grid cards" markdown>

- :material-file-document:{ .lg .middle } **User configuration guide**

    ---

    Configure this element in your Home Assistant setup.

    [:material-arrow-right: Element configuration](../../user-guide/elements/index.md)

- :material-network:{ .lg .middle } **Network modeling**

    ---

    Understand how elements interact in the network model.

    [:material-arrow-right: Network modeling overview](../index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for this element's model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/)

</div>
