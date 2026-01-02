/**
 * Form utility helpers for type-safe access to form data.
 */

/** Entity picker mode type */
export type PickerMode = "entity" | "constant" | "both";

/** Get string from formData with fallback */
export const str = (val: unknown, fallback = ""): string =>
  typeof val === "string" ? val : fallback;

/** Get number from formData with fallback */
export const num = (val: unknown, fallback: number): number =>
  typeof val === "number" ? val : fallback;

/** Get boolean from formData with fallback */
export const bool = (val: unknown, fallback: boolean): boolean =>
  typeof val === "boolean" ? val : fallback;

/** Get entity picker mode from formData with fallback */
export const mode = (val: unknown, fallback: PickerMode): PickerMode => {
  if (val === "entity" || val === "constant" || val === "both") {
    return val;
  }
  return fallback;
};
