# HAEO Pyodide WASM Build

Run HAEO's optimization engine entirely in the browser using Pyodide (Python in WebAssembly).

## Architecture

```
Browser
├── Pyodide (Python 3.12 in WASM)
│   ├── numpy (from Pyodide CDN)
│   ├── highspy (WASM wheel)
│   └── haeo-core (pure Python wheel)
├── solver_shim.py (standalone solver entry point)
└── Forecast Card (Preact, rendered in Storybook)
```

HAEO's `custom_components/haeo/core/` has zero Home Assistant imports — the entire optimization
pipeline runs standalone. The `solver_shim.py` provides mock state classes and a `solve_scenario()`
function that bridges JSON scenario data to the optimizer.

## Components

| File             | Purpose                                                    |
| ---------------- | ---------------------------------------------------------- |
| `solver_shim.py` | Standalone solver entry point (mock HA state, JSON in/out) |
| `build.sh`       | Builds the haeo-core pure-Python wheel into `dist/`        |
| `dist/`          | Build output directory (gitignored)                        |

## Building haeo-core wheel

```bash
./wasm/build.sh
```

This reads the version from `pyproject.toml`, packages `custom_components/haeo/core/` into a
pure-Python wheel, and outputs it to `wasm/dist/`.

## Building highspy WASM wheel

### Prerequisites

- Python 3.12+
- Emscripten SDK 3.1.58
- pyodide-build 0.29.3

### Build steps

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

Copy the resulting `highspy-*.whl` to `wasm/dist/`.

### Key build flags

| Flag                               | Purpose                                                  |
| ---------------------------------- | -------------------------------------------------------- |
| `ZLIB=OFF`                         | zlib unavailable in WASM                                 |
| `FAST_BUILD=ON`                    | Uses code path with `include(python-highs)` for pybind11 |
| `PYTHON_BUILD_SETUP=ON`            | Enables Python bindings build                            |
| `CMAKE_GENERATOR="Unix Makefiles"` | Required (Ninja triggers ARG_MAX on link)                |
| `add_subdirectory(app)` removed    | CLI executable can't link in WASM                        |

### Version compatibility

| Component     | Version |
| ------------- | ------- |
| Pyodide (npm) | 0.27.7  |
| pyodide-build | 0.29.3  |
| Emscripten    | 3.1.58  |
| Python        | 3.12    |
| HiGHS         | 1.14.0  |
| pybind11      | 3.0.4   |

## Running via Storybook

The Storybook story (`frontend/haeo-forecast-card/src/components/WasmOptimization.stories.tsx`)
is the canonical way to run and test the WASM build. It:

1. Loads Pyodide from CDN
2. Installs wheels from `wasm/dist/` (served via Storybook's `staticDirs`)
3. Executes `solver_shim.py` to define the solver function
4. Runs scenarios interactively with the forecast card rendering results

```bash
# Build wheels first
./wasm/build.sh

# Run Storybook
cd frontend/haeo-forecast-card
npm run storybook
```

Navigate to **Live > WASMOptimization** to run scenarios interactively.
