<p align="center">
    <img src="docs/assets/logo.svg" alt="HAEO Logo" width="512">
</p>

# HAEO - Home Assistant Energy Optimizer

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration) [![GitHub Release](https://img.shields.io/github/release/hass-energy/haeo.svg)](https://github.com/hass-energy/haeo/releases) [![License](https://img.shields.io/github/license/hass-energy/haeo.svg)](LICENSE) [![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://hass-energy.github.io/haeo/)

HAEO (Home Assistant Energy Optimizer) is a custom integration that optimizes your home's energy usage in real-time using linear programming.
It helps you minimize energy costs by intelligently managing battery storage, solar generation, grid import/export, and loads based on electricity prices, forecasts, and system constraints.

## 🎯 Project Philosophy

HAEO follows the Unix philosophy: **do one thing and do it well**.

### What HAEO Does

- ✅ **Energy optimization** using linear programming
- ✅ **Network modeling** with flexible topology
- ✅ **Integration** with Home Assistant's sensor ecosystem

### What HAEO Doesn't Do

HAEO focuses exclusively on optimization and **will not** add features outside this scope:

- ❌ **Solar forecasting** - Use existing integrations like [Open-Meteo Solar Forecast](https://github.com/rany2/ha-open-meteo-solar-forecast) or [Solcast](https://github.com/BJReplay/ha-solcast-solar)
- ❌ **Price fetching** - Use integrations like Amber Electric, Nordpool, or Tibber
- ❌ **Device control** - Use Home Assistant automations
- ❌ **Load forecasting** - Use existing integrations or template sensors

This focused approach means:

- Better integration with the HA ecosystem
- Simpler, more maintainable codebase
- Users can choose best-in-class solutions for each component
- HAEO does optimization exceptionally well

## 📚 Documentation

**[Read the full documentation →](https://hass-energy.github.io/haeo/)**

- **[Installation Guide](https://hass-energy.github.io/haeo/user-guide/installation/)** - Get started with HAEO
- **[Configuration Guide](https://hass-energy.github.io/haeo/user-guide/configuration/)** - Set up your energy system
- **[Element Configuration](https://hass-energy.github.io/haeo/user-guide/elements/)** - Configure batteries, solar, grids, and loads
- **[Mathematical Modeling](https://hass-energy.github.io/haeo/modeling/)** - Understand the optimization
- **[Developer Guide](https://hass-energy.github.io/haeo/developer-guide/)** - Contribute to HAEO
- **[API Reference](https://hass-energy.github.io/haeo/api/)** - Auto-generated API docs

## ✨ Features

- **Real-time Optimization**: Continuously optimizes energy flow across all connected devices
- **Multi-device Support**: Batteries, solar panels, grid connection, loads, and energy flows
- **Price-based Optimization**: Minimizes costs using real-time and forecast electricity prices
- **Solar Integration**: Optimizes solar generation with curtailment support
- **Battery Management**: Smart charging/discharging based on prices and SOC constraints
- **Flexible Configuration**: Easy-to-use UI configuration via Home Assistant
- **Multiple Solver Support**: Choose from HiGHS, GLPK, CBC, and other linear programming solvers
- **Rich Sensors**: Power, energy, cost, and state of charge sensors for all devices

## 🎯 How It Works

HAEO builds an energy network model from your configured devices.
It uses linear programming to find the optimal power flow.
This minimizes your total energy cost over a configurable time horizon (default 48 hours).

### The Optimization Process

1. **Data Collection**: Gathers current state (battery SOC, prices) and forecasts (solar production, loads, price forecasts)
2. **Network Modeling**: Builds a mathematical model representing your energy system with power flow constraints
3. **Constraint Application**: Applies limits (battery capacity, charge rates, grid limits, etc.)
4. **Cost Optimization**: Uses a linear programming solver to minimize total cost
5. **Result Publishing**: Updates Home Assistant sensors with optimal power schedules

### Supported Devices

- **Battery**: Energy storage with configurable capacity, charge/discharge rates, and efficiency
- **Grid**: Bi-directional grid connection with import/export limits and pricing
- **Photovoltaics**: Solar generation with optional curtailment
- **Constant Load**: Fixed power loads
- **Forecast Load**: Variable loads with forecast data
- **Node**: Virtual metering points for grouping energy flows
- **Connection**: Power flow paths between devices with optional constraints

## 📦 Installation

### HACS Installation (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hass-energy&repository=haeo&category=integration)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/hass-energy/haeo`
6. Select "Integration" as the category
7. Click "Add"
8. Search for "HAEO" and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/hass-energy/haeo/releases)
2. Extract the `haeo` folder to your `custom_components` directory
3. Restart Home Assistant

## ⚙️ Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **HAEO**
4. Configure your network:
    - **Name**: A unique name for your energy network
    - **Horizon Hours**: Optimization time horizon (1-168 hours, default 48)
    - **Period Minutes**: Time step for optimization (1-60 minutes, default 5)
    - **Optimizer**: Choose your solver (HiGHS recommended)

### Adding Devices

After creating your network, you can add devices through the integration's options:

#### Battery Configuration

- **Name**: Unique identifier for the battery
- **Capacity**: Total energy capacity in kWh
- **Current Charge Sensor**: Entity ID of sensor providing current SOC (%)
- **Min/Max Charge Level**: Operating range (%)
- **Max Charge/Discharge Power**: Power limits in kW
- **Efficiency**: Round-trip efficiency (0-1, e.g., 0.95 for 95%)
- **Charge/Discharge Costs**: Optional additional costs per kWh

#### Grid Configuration

- **Name**: Identifier for grid connection
- **Import/Export Limits**: Maximum power in kW (optional)
- **Import/Export Prices**: Fixed prices OR forecast sensor entities
    - Use live sensors for real-time pricing
    - Use forecast sensors for time-of-use optimization

#### Photovoltaics Configuration

- **Name**: Identifier for solar system
- **Forecast Sensors**: Entity IDs providing power forecast
- **Curtailment**: Enable if you can curtail (reduce) solar output
- **Production Price**: Value of generated electricity

#### Load Configuration

- **Constant Load**: Fixed power consumption in kW
- **Forecast Load**: Variable load with forecast sensor entities

#### Connections

Define how energy flows between devices:

- **Source/Target**: Connect two devices
- **Min/Max Power**: Optional flow limits
- Bidirectional flows use negative values

## 📊 Sensors

HAEO creates sensors for each device and the network:

### Network Sensors

- **Optimization Cost**: Total optimized cost for the time horizon
- **Optimization Status**: Success, failed, or pending
- **Optimization Duration**: Time taken to solve (seconds)

### Device Sensors

- **Power**: Current optimal power for each device (kW)
- **Energy**: Current energy level (batteries, kWh)
- **State of Charge**: Battery SOC (%)

Each sensor includes forecast attributes with timestamped future values.

## 🔧 Advanced Configuration

### Choosing an Optimizer

HAEO supports multiple linear programming solvers:

- **HiGHS** (Recommended): Fast, open-source, no external dependencies
- **CBC**: COIN-OR solver, good for larger problems
- **GLPK**: GNU Linear Programming Kit
- **SCIP**: Academic solver with strong performance

Install solvers via pip: `pip install pulp[highs]`

### Time Horizon and Resolution

- **Shorter horizons** (12-24h): Faster optimization, less lookahead
- **Longer horizons** (48-168h): Better long-term decisions, slower solve
- **Smaller periods** (5min): Higher resolution, more variables
- **Larger periods** (15-60min): Faster solve, coarser control

Balance these based on your hardware and use case.

## 📈 Example Use Cases

### Solar + Battery + Grid

Optimize when to charge your battery from solar vs. grid based on electricity prices.
This determines when to discharge to maximize savings.

### Time-of-Use Pricing

Automatically shift battery charging to off-peak hours and discharging to peak hours to minimize electricity costs.

### Solar Curtailment

Reduce solar output when grid export prices are negative or very low, preventing paying to export energy.

### Load Shifting

Plan energy-intensive activities during periods of low prices or high solar production.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/hass-energy/haeo.git
cd haeo

# Install dependencies with uv
uv sync

# Run tests
uv run pytest

# Run linters
uv run ruff check
uv run pyright
```

## 🐛 Support

- **Issues**: [GitHub Issues](https://github.com/hass-energy/haeo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/hass-energy/haeo/discussions)

When reporting issues, please include:

- Home Assistant version
- HAEO version
- Integration configuration (sanitized)
- Relevant logs from Home Assistant

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [PuLP](https://github.com/coin-or/pulp) for linear programming
- Inspired by the Home Assistant community's energy optimization needs
- Uses the Home Assistant integration framework

---

**Note**: This integration performs optimization calculations that may be computationally intensive for large networks or long time horizons.
Monitor your Home Assistant instance's performance.
Adjust configuration as needed.
