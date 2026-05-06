# HAEO Pyodide WASM Build

Run HAEO's optimization engine entirely in the browser using Pyodide (Python in WebAssembly).

## Components

- `highspy-1.14.0-cp312-cp312-pyodide_2024_0_wasm32.whl` — HiGHS LP solver compiled to WASM
- `haeo_core-0.4.0-py3-none-any.whl` — HAEO core (pure Python, no HA deps)
- `demo/index.html` — Interactive demo page

## Building highspy WASM wheel

### Prerequisites
- Python 3.12+
- Emscripten SDK 3.1.58
- pyodide-build 0.29.3

### Build Steps

```bash
# Install emsdk
git clone --depth 1 https://github.com/emscripten-core/emsdk.git /emsdk
cd /emsdk && ./emsdk install 3.1.58 && ./emsdk activate 3.1.58
export PATH="/emsdk:/emsdk/upstream/emscripten:$PATH"

# Install pyodide-build
pip install pyodide-build==0.29.3

# Clone HiGHS
git clone --depth 1 --branch v1.14.0 https://github.com/ERGO-Code/HiGHS.git
cd HiGHS

# Patch: remove CLI app build (causes link errors in WASM)
sed -i 's|add_subdirectory(app)|# add_subdirectory(app)|g' CMakeLists.txt

# Build
export CMAKE_ARGS="-DZLIB=OFF -DFAST_BUILD=ON -DPYTHON_BUILD_SETUP=ON -Dpybind11_DIR=$(python3 -c 'import pybind11; print(pybind11.get_cmake_dir())')"
export CMAKE_GENERATOR="Unix Makefiles"
pyodide build --outdir ./dist
```

### Key Build Flags
| Flag | Purpose |
|------|---------|
| `ZLIB=OFF` | zlib unavailable in WASM |
| `FAST_BUILD=ON` | Uses code path with `include(python-highs)` for pybind11 |
| `PYTHON_BUILD_SETUP=ON` | Enables Python bindings build |
| `CMAKE_GENERATOR="Unix Makefiles"` | Required (Ninja triggers ARG_MAX on link) |
| `add_subdirectory(app)` removed | CLI executable can't link in WASM |

### Version Compatibility
| Component | Version |
|-----------|---------|
| Pyodide (npm) | 0.27.7 |
| pyodide-build | 0.29.3 |
| Emscripten | 3.1.58 |
| Python | 3.12 |
| HiGHS | 1.14.0 |
| pybind11 | 3.0.4 |

## Building haeo-core wheel

```bash
cd haeo
pip install build
# Build pure-Python wheel from core modules (no HA deps)
python3 -m build --wheel wasm/haeo-core-pkg/
```

## Running the Demo

Serve the `demo/` directory with any HTTP server:
```bash
cd wasm/demo
python3 -m http.server 8080
```

Open http://localhost:8080 — the demo loads Pyodide, installs the wheels, and runs scenarios interactively.

## Architecture

```
Browser
├── Pyodide (Python 3.12 in WASM)
│   ├── numpy (from Pyodide CDN)
│   ├── highspy (WASM wheel, 1.5MB)
│   └── haeo-core (pure Python wheel, 134KB)
├── Scenario JSON (fetched from GitHub)
└── Forecast Card (Preact, rendered client-side)
```

HAEO's `custom_components/haeo/core/` has zero homeassistant imports — the entire optimization pipeline runs standalone.
