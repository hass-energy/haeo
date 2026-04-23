import js from "@eslint/js";
import prettierConfig from "eslint-config-prettier";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: ["node_modules", "coverage", "storybook-static", "previews"],
  },
  {
    files: ["**/*.ts", "**/*.tsx"],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommendedTypeChecked,
      ...tseslint.configs.stylisticTypeChecked,
      prettierConfig,
    ],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      "@typescript-eslint/consistent-type-imports": [
        "error",
        {
          prefer: "type-imports",
          fixStyle: "inline-type-imports",
        },
      ],
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-misused-promises": "error",
      "@typescript-eslint/require-await": "error",
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unnecessary-condition": "error",
      "@typescript-eslint/unbound-method": "off",
      "@typescript-eslint/consistent-type-definitions": ["error", "interface"],
      "@typescript-eslint/array-type": "off",
      "@typescript-eslint/no-base-to-string": "error",
      "@typescript-eslint/prefer-nullish-coalescing": "off",
      "@typescript-eslint/prefer-for-of": "error",
      "no-console": "error",
      "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
      "@typescript-eslint/strict-boolean-expressions": "error",
    },
  },
  {
    files: ["tests/**/*.ts", "tests/**/*.tsx", "**/*.stories.tsx", ".storybook/**/*.ts"],
    rules: {
      "@typescript-eslint/no-unnecessary-condition": "off",
      "@typescript-eslint/strict-boolean-expressions": "off",
      "no-console": "off",
    },
  }
);
