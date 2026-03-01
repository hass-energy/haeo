# [Model Element Name]

Brief description of this model element's role in the optimization problem (1-2 sentences).
Focus on what decisions the optimizer makes regarding this element.

!!! note "Model Layer element"

    This page documents a **Model Layer** element—the building blocks of HAEO's linear programming formulation.
    Model Layer elements are composed by Device Layer elements through the adapter layer.

## Model Formulation

This section describes the mathematical optimization model for this element.
Present the formulation in standard optimization notation.

### Parameters

List all parameters (inputs) required by this element's model.
Distinguish between configuration-derived parameters and sensor-derived data.

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

## Next Steps

!!! note "Template Instructions"

    When using this template:

    1. Replace `element.py` in the source code link with the actual model filename (e.g., `battery.py`)
    2. Curate Next Steps cards to show 3-4 most relevant actions for readers of this page
    3. Link to related Model Layer elements and relevant user-facing documentation
    4. Do NOT enumerate which Device Layer elements use this model (that's reverse enumeration)

<div class="grid cards" markdown>

- :material-file-document:{ .lg .middle } **User guide**

    ---

    Learn how to configure elements in Home Assistant.

    [:material-arrow-right: Elements overview](../../user-guide/elements/index.md)

- :material-network:{ .lg .middle } **Network optimization**

    ---

    Understand how model elements interact in the network.

    [:material-arrow-right: Network optimization overview](../index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for this model element.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/element.py)

</div>
