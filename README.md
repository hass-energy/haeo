<p align="center">
    <img src="docs/assets/logo.svg" alt="HAEO Logo" width="512">
</p>

# HAEO - Home Assistant Energy Optimizer

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration) [![GitHub Release](https://img.shields.io/github/release/hass-energy/haeo.svg)](https://github.com/hass-energy/haeo/releases) [![License](https://img.shields.io/github/license/hass-energy/haeo.svg)](LICENSE) [![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://hass-energy.github.io/haeo/) [![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow.svg)](https://buymeacoffee.com/haeo.io)

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
- ❌ **Load forecasting** - Use [HAFO](https://hafo.haeo.io) or other integrations

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
- **HiGHS Solver**: Fast, reliable linear programming via bundled `highspy` bindings
- **Rich Sensors**: Power, energy, cost, and state of charge sensors for all devices

## 🎯 How It Works

HAEO builds an energy network model from your configured elements.
It uses linear programming to find the optimal power flow that minimizes total energy cost over a **multi-tier planning horizon** (fine resolution near-term, coarser intervals further out).

Optimization runs when input data changes (debounced) and when the horizon advances past each finest-tier period boundary, so recommendations stay current as prices and forecasts update.
See the [configuration guide](https://hass-energy.github.io/haeo/user-guide/configuration/) and [data updates guide](https://hass-energy.github.io/haeo/user-guide/data-updates/) for details.

### The Optimization Process

1. **Data Collection**: Gathers current state (battery SOC, prices) and forecasts (solar production, loads, price forecasts)
2. **Network Modeling**: Builds a mathematical model representing your energy system with power flow constraints
3. **Constraint Application**: Applies limits (battery capacity, charge rates, grid limits, etc.)
4. **Cost Optimization**: Uses HiGHS to minimize total cost over the tiered horizon
5. **Result Publishing**: Updates Home Assistant sensors with current optimal power and forecast attributes

### Supported Elements

**Standard elements** (most setups):

- **Battery**: Energy storage with configurable capacity, charge/discharge rates, and efficiency
- **Grid**: Bi-directional grid with import/export limits and pricing
- **Solar**: Solar generation with optional curtailment
- **Load**: Fixed or forecast-based consumption
- **Inverter**: AC/DC conversion between elements

**Advanced Mode** (optional, for custom topologies):

- **Node**: Virtual power balance points
- **Connection**: Explicit power flow paths between elements
- **Battery Section**: Direct model-layer battery access

Pricing and economic incentives use **policy** rules configured on elements.
See the [elements documentation](https://hass-energy.github.io/haeo/user-guide/elements/) for full details.

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
4. Configure your hub:
    - **Name**: A unique name for your energy network
    - **Planning horizon**: Preset (2, 3, 5, or 7 days) or **Custom** tier configuration
    - **Advanced settings** (optional): Debounce window, Advanced Mode, forecast recording

If you select **Custom**, configure up to four **tiers** (interval count and duration in minutes) for near-term precision and long-term lookahead.

See the [configuration guide](https://hass-energy.github.io/haeo/user-guide/configuration/) for tier tuning advice.

### Adding Elements

After creating your hub, add elements from the hub integration card:

1. Open your **HAEO** integration
2. Click the **:** menu → **Add Entry**
3. Choose an element type and complete the configuration flow

#### Battery Configuration

- **Name**: Unique identifier for the battery
- **Capacity**: Total energy capacity in kWh
- **Current Charge Sensor**: Entity ID of sensor providing current SOC (%)
- **Min/Max Charge Level**: Operating range (%)
- **Max Charge/Discharge Power**: Power limits in kW
- **Efficiency**: Round-trip efficiency (0-1, e.g., 0.95 for 95%)
- **Charge/Discharge Costs**: Optional additional costs per kWh

#### Grid Configuration

- **Name**: Identifier for grid
- **Import/Export Limits**: Maximum power in kW (optional)
- **Import/Export Prices**: Fixed prices OR forecast sensor entities
    - Use live sensors for real-time pricing
    - Use forecast sensors for time-of-use optimization

#### Solar Configuration

- **Name**: Identifier for solar system
- **Forecast Sensors**: Entity IDs providing power forecast
- **Curtailment**: Enable if you can curtail (reduce) solar output
- **Production Price**: Value of generated electricity

#### Load Configuration

- **Name**: Identifier for the load
- **Power**: Fixed value or forecast sensor entities for variable consumption

#### Connections (Advanced Mode)

Define explicit power flow paths between elements:

- **Source/Target**: Connect two elements
- **Min/Max Power**: Optional flow limits

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

### Optimization Solver

HAEO uses the **HiGHS** linear programming solver via the `highspy` Python bindings.
HiGHS is the only supported solver and is bundled with the integration (no external binaries required).

### Planning Horizon and Tiers

HAEO divides the planning horizon into up to four **tiers**, each with its own interval duration:

- **Near-term tiers** (for example, 1-minute intervals): Higher resolution for immediate decisions; match your fastest-updating price or forecast sensors
- **Long-term tiers** (for example, 30–60 minute intervals): Coarser lookahead when distant forecasts are less reliable

Tuning tips:

- Use a **shorter preset** or reduce tier 4 count for faster solves
- Use a **longer preset** for more multi-day lookahead
- Disable a tier by setting its count to zero

Balance tier counts and durations based on your hardware and use case.
See the [custom tiers section](https://hass-energy.github.io/haeo/user-guide/configuration/#custom-tiers) in the documentation.

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

- Built with [HiGHS](https://highs.dev/) for linear programming via the `highspy` Python bindings
- Special mention to [EMHASS](https://github.com/davidusb-geek/emhass) for bringing out my competitive nature and proving that healthy competition drives innovation
- Uses the Home Assistant integration framework

---

**Note**: This integration performs optimization calculations that may be computationally intensive for large networks or long time horizons.
Monitor your Home Assistant instance's performance.
Adjust configuration as needed.
