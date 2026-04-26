import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    {
      name: "css-as-text",
      enforce: "pre",
      transform(code, id) {
        if (id.endsWith("/src/styles.css")) {
          return { code: `export default ${JSON.stringify(code)};`, map: null };
        }
      },
    },
  ],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    exclude: ["tests/**", "node_modules/**"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: ["src/**/*.ts", "src/**/*.tsx"],
      exclude: [
        "src/index.ts",
        "src/css.d.ts",
        "src/custom-elements.d.ts",
        "src/test-setup.ts",
        "src/types.ts",
        "src/**/*.test.ts",
        "src/**/*.test.tsx",
        "src/**/*.stories.tsx",
        "src/fixtures/**",
      ],
      thresholds: {
        lines: 83,
        functions: 85,
        branches: 75,
        statements: 83,
      },
    },
  },
});
