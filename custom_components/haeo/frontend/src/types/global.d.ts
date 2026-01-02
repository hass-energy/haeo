/* CSS module declarations */
declare module "*.css" {
  const content: Record<string, string>;
  export default content;
}

/* Image module declarations */
declare module "*.svg" {
  const content: string;
  export default content;
}

declare module "*.png" {
  const content: string;
  export default content;
}
