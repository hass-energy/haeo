interface ConfigFormSchema {
  name: string;
  required?: boolean;
  selector: Record<string, unknown>;
}

interface ConfigFormDefinition {
  schema: ConfigFormSchema[];
  computeLabel: (schema: { name: string }) => string | undefined;
  computeHelper: (schema: { name: string }) => string | undefined;
}

export function buildHubConfigForm(): ConfigFormDefinition {
  return {
    schema: [
      { name: "title", selector: { text: {} } },
      {
        name: "hub_entry_id",
        required: true,
        selector: { config_entry: { integration: "haeo" } },
      },
    ],
    computeLabel: (schema) => {
      if (schema.name === "title") {
        return "Title";
      }
      if (schema.name === "hub_entry_id") {
        return "HAEO hub";
      }
      return undefined;
    },
    computeHelper: (schema) => {
      if (schema.name === "hub_entry_id") {
        return "Select the HAEO system this card should display.";
      }
      return undefined;
    },
  };
}
