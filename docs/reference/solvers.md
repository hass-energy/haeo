# LP Solver Reference

Linear programming solvers supported by HAEO.

## Solver Comparison

| Solver | Speed | License | Installation |
|--------|-------|---------|--------------|
| HiGHS | Very Fast | MIT | Included with PuLP |
| CBC | Fast | EPL | `pip install pulp[cbc]` |
| GLPK | Medium | GPL | `pip install pulp[glpk]` |
| CPLEX | Very Fast | Commercial | Separate install + license |
| Gurobi | Very Fast | Commercial | Separate install + license |

## Recommended: HiGHS

HiGHS is the default and recommended solver:

- **Fast**: Modern C++ implementation
- **Open source**: MIT licensed
- **No setup**: Included with PuLP
- **Well maintained**: Active development

## Configuration

Select solver in network configuration:

```yaml
Optimizer: HiGHS
```

Available options:
- `HiGHS`
- `PULP_CBC_CMD`
- `GLPK_CMD`
- `CPLEX_CMD`
- `GUROBI_CMD`

## Installing Additional Solvers

### CBC

```bash
pip install pulp[cbc]
```

### GLPK

```bash
pip install pulp[glpk]
```

### Commercial Solvers

CPLEX and Gurobi require:
1. Separate installation
2. Valid license
3. PuLP configuration

See solver documentation for setup.

## Performance Notes

For typical home energy systems (1-5 entities, 48h horizon, 5min periods):

- **HiGHS**: 0.5-2 seconds
- **CBC**: 1-3 seconds
- **GLPK**: 2-5 seconds

Commercial solvers offer marginal improvements for such small problems.

For larger systems (10+ entities, 168h horizon), commercial solvers may be beneficial.
