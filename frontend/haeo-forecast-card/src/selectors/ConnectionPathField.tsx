import {
  mdiArrowDown,
  mdiArrowUp,
  mdiClose,
  mdiCurrencyUsd,
  mdiPercentOutline,
  mdiPlus,
  mdiSpeedometer,
} from "@mdi/js";
import { useState } from "preact/hooks";
import type { JSX } from "preact";

import { NODE_STYLES } from "../element-styles";
import { InputField } from "./InputField";
import type { FieldContext } from "./selector-element";
import type { ConnectionPath, ConnectionPathConfig, InputValue, PathSegment } from "./types";

/** Each kind of segment's icon; the kind's name comes from the integration's translations. */
const SEGMENT_ICONS: Record<string, string> = {
  power_limit: mdiSpeedometer,
  pricing: mdiCurrencyUsd,
  efficiency: mdiPercentOutline,
};

function Icon({ path }: { path: string }): JSX.Element {
  return (
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d={path} />
    </svg>
  );
}

function elementIcon(elementType: string): string {
  return (NODE_STYLES[elementType] ?? NODE_STYLES["unknown"])?.icon ?? "";
}

/** Move the item at `from` to `to` in a copy of the list. */
function moved<T>(items: T[], from: number, to: number): T[] {
  const next = [...items];
  const [item] = next.splice(from, 1);
  if (item !== undefined) {
    next.splice(to, 0, item);
  }
  return next;
}

/**
 * A connection as a chain, read top to bottom in the direction power flows: the
 * source, each segment in the order it applies, then the target. Each segment
 * is a card holding its one input, which can be moved earlier or later or
 * removed, and the (+) on each link inserts a new segment at that point.
 */
export function ConnectionPathField(props: FieldContext<ConnectionPathConfig, ConnectionPath>): JSX.Element {
  const { config, value, hass, label, helper, required, disabled, t, onChange } = props;
  const [adding, setAdding] = useState<number | null>(null);
  const path: ConnectionPath = value ?? {
    source: config.participants[0]?.name ?? "",
    target: config.participants[1]?.name ?? "",
    segments: [],
  };
  const segments = path.segments;
  const kinds = Object.keys(config.segment_types);
  const kindName = (kind: string): string => t(`connection_path.options.${kind}`);

  const setSegments = (next: PathSegment[]): void => {
    onChange({ ...path, segments: next });
  };

  const insert = (index: number, kind: string): void => {
    const field = config.segment_types[kind]?.field ?? "";
    setSegments([...segments.slice(0, index), { segment_type: kind, [field]: undefined }, ...segments.slice(index)]);
    setAdding(null);
  };

  const endpoint = (role: "source" | "target"): JSX.Element => {
    const selected = path[role];
    const participant = config.participants.find((item) => item.name === selected);
    return (
      <label class="path-endpoint">
        <span class="path-endpoint-icon" aria-hidden="true">
          {elementIcon(participant?.element_type ?? "")}
        </span>
        <select
          aria-label={t(`connection_path.options.${role}`)}
          disabled={disabled}
          value={selected}
          onChange={(event) => onChange({ ...path, [role]: event.currentTarget.value })}
        >
          {config.participants.map((item) => (
            <option key={item.name} value={item.name}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
    );
  };

  const link = (index: number): JSX.Element => (
    <div class="path-link">
      <div class="path-line" aria-hidden="true" />
      {adding === index ? (
        <div class="path-kinds">
          {kinds.map((kind) => (
            <button key={kind} type="button" class="path-kind" disabled={disabled} onClick={() => insert(index, kind)}>
              <Icon path={SEGMENT_ICONS[kind] ?? mdiPlus} />
              {kindName(kind)}
            </button>
          ))}
          <button
            type="button"
            class="path-control"
            aria-label={t("connection_path.options.cancel")}
            onClick={() => setAdding(null)}
          >
            <Icon path={mdiClose} />
          </button>
        </div>
      ) : (
        <button
          type="button"
          class="path-add"
          disabled={disabled}
          aria-label={t("connection_path.options.add_segment")}
          onClick={() => setAdding(index)}
        >
          <Icon path={mdiPlus} />
        </button>
      )}
      <div class="path-line path-arrow" aria-hidden="true" />
    </div>
  );

  return (
    <div class={`field${disabled ? " disabled" : ""}`}>
      <div class="label">
        {label}
        {required ? " *" : ""}
      </div>
      <div class="path">
        {endpoint("source")}
        {link(0)}
        {segments.map((segment, index) => {
          const kind = config.segment_types[segment.segment_type];
          const name = kindName(segment.segment_type);
          if (kind === undefined) {
            return null;
          }
          return (
            <div key={index} class="path-step">
              <div class="path-segment">
                <div class="path-segment-head">
                  <Icon path={SEGMENT_ICONS[segment.segment_type] ?? mdiPlus} />
                  <span class="path-segment-name">{name}</span>
                  <div class="path-controls">
                    <button
                      type="button"
                      class="path-control"
                      disabled={disabled || index === 0}
                      aria-label={t("connection_path.options.move_earlier", { segment: name })}
                      onClick={() => setSegments(moved(segments, index, index - 1))}
                    >
                      <Icon path={mdiArrowUp} />
                    </button>
                    <button
                      type="button"
                      class="path-control"
                      disabled={disabled || index === segments.length - 1}
                      aria-label={t("connection_path.options.move_later", { segment: name })}
                      onClick={() => setSegments(moved(segments, index, index + 1))}
                    >
                      <Icon path={mdiArrowDown} />
                    </button>
                    <button
                      type="button"
                      class="path-control"
                      disabled={disabled}
                      aria-label={t("connection_path.options.remove_segment", { segment: name })}
                      onClick={() => setSegments(segments.filter((_, other) => other !== index))}
                    >
                      <Icon path={mdiClose} />
                    </button>
                  </div>
                </div>
                <InputField
                  config={kind.input}
                  value={segment[kind.field] as InputValue | undefined}
                  hass={hass}
                  label={name}
                  labelHidden={true}
                  required={true}
                  disabled={disabled}
                  t={t}
                  onChange={(input) =>
                    setSegments(segments.map((other, at) => (at === index ? { ...other, [kind.field]: input } : other)))
                  }
                />
              </div>
              {link(index + 1)}
            </div>
          );
        })}
        {endpoint("target")}
      </div>
      {helper !== undefined && helper !== "" && <div class="helper">{helper}</div>}
    </div>
  );
}
