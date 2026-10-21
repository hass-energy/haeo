<p align="center">
    <img src="docs/assets/logo.svg" alt="HAEO Logo" width="512">
</p>

# HAEO - Home Assistant Energy Optimizer

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration) [![GitHub Release](https://img.shields.io/github/release/hass-energy/haeo.svg)](https://github.com/hass-energy/haeo/releases) [![License](https://img.shields.io/github/license/hass-energy/haeo.svg)](LICENSE) [![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://haeo.io/latest/) [![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow.svg)](https://buymeacoffee.com/haeo.io)

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

**[Read the full documentation →](https://haeo.io/latest/)**

- **[Installation Guide](https://haeo.io/latest/user-guide/installation/)** - Get started with HAEO
- **[Configuration Guide](https://haeo.io/latest/user-guide/configuration/)** - Set up your energy system
- **[Element Configuration](https://haeo.io/latest/user-guide/elements/)** - Configure batteries, solar, grids, and loads
- **[Mathematical Modeling](https://haeo.io/latest/modeling/)** - Understand the optimization
- **[Developer Guide](https://haeo.io/latest/developer-guide/)** - Contribute to HAEO

## ✨ Features

- **Real-time Optimization**: Continuously optimizes energy flow across all connected devices
- **Multi-device Support**: Batteries, solar panels, grid connection, loads, and energy flows
- **Power Policies**: Source→destination pricing so the optimizer values solar, grid, and battery flows differently ([guide](https://haeo.io/latest/walkthroughs/power-policies/))
- **Price-based Optimization**: Minimizes costs using real-time and forecast electricity prices
- **Solar Integration**: Optimizes solar generation with curtailment support
- **Battery Management**: Smart charging/discharging based on prices and SOC constraints
- **Flexible Configuration**: Easy-to-use UI configuration via Home Assistant
- **HiGHS Solver**: Fast, reliable linear programming via bundled `highspy` bindings
- **Rich Sensors**: Power, energy, cost, and state of charge sensors for all devices

## 🎯 How It Works

HAEO builds an energy network model from your configured elements.
It uses linear programming to find the optimal power flow that minimizes total energy cost over a **multi-resolution planning horizon** (fine resolution near-term, coarser intervals further out).

Optimization runs when input data changes (debounced) and when the planning horizon advances, so recommendations stay current as prices and forecasts update.
See the [configuration guide](https://haeo.io/latest/user-guide/configuration/) and [data updates guide](https://haeo.io/latest/user-guide/data-updates/) for details.

### The Optimization Process

1. **Data Collection**: Gathers current state (battery SOC, prices) and forecasts (solar production, loads, price forecasts)
2. **Network Modeling**: Builds a mathematical model representing your energy system with power flow constraints
3. **Constraint Application**: Applies limits (battery capacity, charge rates, grid limits, etc.)
4. **Cost Optimization**: Uses HiGHS to minimize total cost over the planning horizon
5. **Result Publishing**: Updates Home Assistant sensors with current optimal power and forecast attributes

### Elements

Elements are the devices you add to describe your energy system.
They store energy (such as home batteries and electric vehicles), generate it (such as solar), consume it (fixed and flexible loads), or exchange it with the grid.
Connections and junctions route power between elements, and inverters convert between AC and DC.
[Power policies](https://haeo.io/latest/walkthroughs/power-policies/) price energy by where it comes from and where it goes, for example cheap solar to your loads but paid solar to export.

See the [elements documentation](https://haeo.io/latest/user-guide/elements/) for every element and how to configure it.

## 📦 Installation

### HACS installation (recommended)

HAEO is published in the [default HACS store](https://github.com/hacs/default).
You do not need to [add a custom repository](https://hacs.xyz/docs/faq/custom_repositories/).
See the [installation guide](https://haeo.io/latest/user-guide/installation/) for step-by-step instructions.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hass-energy&repository=haeo&category=integration)

You can use the My Home Assistant link above to open HAEO directly in HACS, then download and restart Home Assistant.

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
    - **Planning horizon**: Preset (2, 3, 5, or 7 days) or a forecast sensor whose forecast times set the periods
    - **Advanced settings** (optional): Expose raw model elements

See the [configuration guide](https://haeo.io/latest/user-guide/configuration/#planning-horizon) for how to choose a planning horizon.
After setup, **Configure** on the hub entry also offers the debounce window, forecast recording, and **Relax impossible plans**, which keeps planning when your forecasts ask for more than your system can do.
See [editing hub settings](https://haeo.io/latest/user-guide/configuration/#editing-hub-settings) for details.

### Adding Elements

After creating your hub, add elements from the hub integration card:

1. Open your **HAEO** integration
2. Click the **menu button** (three vertical dots, top right) → **Add Entry**
3. Choose an element type and complete the configuration flow

Each element has its own page in the [elements documentation](https://haeo.io/latest/user-guide/elements/) describing its fields, for example the [battery](https://haeo.io/latest/user-guide/elements/battery/), [grid](https://haeo.io/latest/user-guide/elements/grid/), [solar](https://haeo.io/latest/user-guide/elements/solar/), and [load](https://haeo.io/latest/user-guide/elements/load/) pages.

## 📊 Sensors

HAEO creates sensors for each element and for the optimizer itself.

### Optimizer sensors

The **Optimizer** device reports on each optimization run:

- **Cost** (`sensor.optimizer_cost`): Total optimized cost over the planning horizon
- **Status** (`sensor.optimizer_status`): Whether the last optimization succeeded
- **Duration** (`sensor.optimizer_duration`): Time taken to solve, in seconds

### Element sensors

Each element reports its planned power, and storage elements also report stored energy and state of charge.
Each sensor includes forecast attributes with timestamped future values.

See [understanding optimization results](https://haeo.io/latest/user-guide/optimization/) for how to read these sensors.

## 🔧 Advanced Configuration

### Optimization Solver

HAEO uses the **HiGHS** linear programming solver via the `highspy` Python bindings.
HiGHS is the only supported solver and is bundled with the integration (no external binaries required).

### Planning Horizon

HAEO divides the planning horizon into periods of varying length:

- **Near-term periods** (for example, 1-minute intervals): Higher resolution for immediate decisions
- **Long-term periods** (for example, 30–60 minute intervals): Coarser lookahead when distant forecasts are less reliable

Presets cover 2, 3, 5, or 7 days with this layout.
For a different layout, choose a forecast sensor whose forecast times mark each period boundary.

Tuning tips:

- Use a **shorter preset** or a forecast sensor with fewer periods for faster solves
- Use a **longer preset** for more multi-day lookahead

See the [planning horizon section](https://haeo.io/latest/user-guide/configuration/#planning-horizon) in the documentation.

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
