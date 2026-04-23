import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: ["src/**/*.ts", "src/**/*.tsx"],
      exclude: [
        "src/index.ts",
        "src/custom-elements.d.ts",
        "src/types.ts",
        "src/**/*.stories.tsx",
        "src/fixtures/**",
        "src/components/ResponsiveStoryFrame.tsx",
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
