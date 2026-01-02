/**
 * EntityPicker component for selecting Home Assistant entities or entering constant values.
 * Supports three modes:
 * - "entity": Select a single entity
 * - "constant": Enter a constant numeric value
 * - "both": Toggle between entity and constant modes
 */

import { useState, useRef, useEffect, useMemo } from "react";
import { useConnection } from "../context/ConnectionContext";
import "./EntityPicker.css";

interface EntityPickerProps {
  id: string;
  label: string;
  mode: "entity" | "constant" | "both";
  value: string | string[];
  constantValue?: number;
  onChange: (
    mode: "entity" | "constant",
    value: string | string[],
    constantValue?: number,
  ) => void;
  unit?: string;
  description?: string;
  required?: boolean;
  disabled?: boolean;
  multiple?: boolean;
  domainFilter?: string[];
  deviceClassFilter?: string[];
}

function EntityPicker({
  id,
  label,
  mode,
  value,
  constantValue = 0,
  onChange,
  unit = "",
  description,
  required = false,
  disabled = false,
  multiple = false,
  domainFilter,
  deviceClassFilter,
}: EntityPickerProps) {
  const { entities, entityRegistry } = useConnection();
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [activeMode, setActiveMode] = useState<"entity" | "constant">(
    mode === "constant" ? "constant" : "entity",
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Create a map of entity registry entries for quick lookup
  const entityRegistryMap = useMemo(() => {
    const map: Record<string, (typeof entityRegistry)[0]> = {};
    for (const entry of entityRegistry) {
      map[entry.entity_id] = entry;
    }
    return map;
  }, [entityRegistry]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Filter entities based on search and filters
  const filteredEntities = useMemo(() => {
    return Object.entries(entities)
      .filter(([entityId, state]) => {
        // Domain filter
        if (domainFilter && domainFilter.length > 0) {
          const domain = entityId.split(".")[0];
          if (!domainFilter.includes(domain)) return false;
        }

        // Device class filter
        if (deviceClassFilter && deviceClassFilter.length > 0) {
          const deviceClass = state.attributes?.device_class;
          if (!deviceClass || !deviceClassFilter.includes(deviceClass))
            return false;
        }

        // Search filter
        if (search) {
          const searchLower = search.toLowerCase();
          const friendlyName =
            state.attributes?.friendly_name?.toLowerCase() || "";
          return (
            entityId.toLowerCase().includes(searchLower) ||
            friendlyName.includes(searchLower)
          );
        }

        return true;
      })
      .sort(([a], [b]) => a.localeCompare(b));
  }, [entities, domainFilter, deviceClassFilter, search]);

  // Get display name for an entity
  const getEntityDisplayName = (entityId: string): string => {
    const state = entities[entityId];
    const registryEntry = entityRegistryMap[entityId];

    if (registryEntry?.name) return registryEntry.name;
    if (state?.attributes?.friendly_name) return state.attributes.friendly_name;
    return entityId;
  };

  // Handle entity selection
  const handleSelectEntity = (entityId: string) => {
    if (multiple) {
      const currentValues = Array.isArray(value) ? value : value ? [value] : [];
      const newValues = currentValues.includes(entityId)
        ? currentValues.filter((v) => v !== entityId)
        : [...currentValues, entityId];
      onChange("entity", newValues);
    } else {
      onChange("entity", entityId);
      setIsOpen(false);
      setSearch("");
    }
  };

  // Handle mode toggle
  const handleModeToggle = (newMode: "entity" | "constant") => {
    setActiveMode(newMode);
    if (newMode === "constant") {
      onChange("constant", "", constantValue);
    } else {
      onChange("entity", Array.isArray(value) ? value : value || "");
    }
  };

  // Handle constant value change
  const handleConstantChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseFloat(e.target.value) || 0;
    onChange("constant", "", newValue);
  };

  // Get selected entities for display
  const selectedEntities = Array.isArray(value)
    ? value
    : value
      ? [value]
      : [];

  return (
    <div className="entity-picker" ref={containerRef}>
      <label htmlFor={id} className="entity-picker__label">
        {label}
        {required && <span className="entity-picker__required">*</span>}
        {unit && <span className="entity-picker__unit">({unit})</span>}
      </label>

      {/* Mode toggle for "both" mode */}
      {mode === "both" && (
        <div className="entity-picker__mode-toggle">
          <button
            type="button"
            className={`entity-picker__mode-btn ${activeMode === "entity" ? "entity-picker__mode-btn--active" : ""}`}
            onClick={() => handleModeToggle("entity")}
            disabled={disabled}
          >
            Entity
          </button>
          <button
            type="button"
            className={`entity-picker__mode-btn ${activeMode === "constant" ? "entity-picker__mode-btn--active" : ""}`}
            onClick={() => handleModeToggle("constant")}
            disabled={disabled}
          >
            Constant
          </button>
        </div>
      )}

      {/* Constant value input */}
      {(mode === "constant" || (mode === "both" && activeMode === "constant")) && (
        <div className="entity-picker__constant">
          <input
            type="number"
            id={id}
            value={constantValue}
            onChange={handleConstantChange}
            disabled={disabled}
            className="entity-picker__constant-input"
          />
          {unit && <span className="entity-picker__constant-unit">{unit}</span>}
        </div>
      )}

      {/* Entity picker */}
      {(mode === "entity" || (mode === "both" && activeMode === "entity")) && (
        <div className="entity-picker__dropdown">
          <div
            className={`entity-picker__trigger ${isOpen ? "entity-picker__trigger--open" : ""}`}
            onClick={() => !disabled && setIsOpen(!isOpen)}
            role="combobox"
            aria-expanded={isOpen}
            aria-haspopup="listbox"
            aria-controls={`${id}-listbox`}
            tabIndex={disabled ? -1 : 0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                !disabled && setIsOpen(!isOpen);
              }
            }}
          >
            {selectedEntities.length > 0 ? (
              <div className="entity-picker__selected">
                {selectedEntities.map((entityId) => (
                  <span key={entityId} className="entity-picker__chip">
                    {getEntityDisplayName(entityId)}
                    {multiple && (
                      <button
                        type="button"
                        className="entity-picker__chip-remove"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectEntity(entityId);
                        }}
                        aria-label={`Remove ${getEntityDisplayName(entityId)}`}
                      >
                        ×
                      </button>
                    )}
                  </span>
                ))}
              </div>
            ) : (
              <span className="entity-picker__placeholder">
                Select an entity...
              </span>
            )}
            <span className="entity-picker__arrow">▼</span>
          </div>

          {isOpen && (
            <div
              className="entity-picker__menu"
              id={`${id}-listbox`}
              role="listbox"
            >
              <div className="entity-picker__search">
                <input
                  ref={inputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search entities..."
                  className="entity-picker__search-input"
                  autoFocus
                />
              </div>
              <div className="entity-picker__options">
                {filteredEntities.length === 0 ? (
                  <div className="entity-picker__empty">No entities found</div>
                ) : (
                  filteredEntities.map(([entityId, state]) => (
                    <div
                      key={entityId}
                      className={`entity-picker__option ${selectedEntities.includes(entityId) ? "entity-picker__option--selected" : ""}`}
                      onClick={() => handleSelectEntity(entityId)}
                      role="option"
                      aria-selected={selectedEntities.includes(entityId)}
                    >
                      <div className="entity-picker__option-content">
                        <span className="entity-picker__option-name">
                          {state.attributes?.friendly_name || entityId}
                        </span>
                        <span className="entity-picker__option-id">
                          {entityId}
                        </span>
                      </div>
                      <span className="entity-picker__option-state">
                        {state.state}
                        {state.attributes?.unit_of_measurement &&
                          ` ${state.attributes.unit_of_measurement}`}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {description && (
        <p className="entity-picker__description">{description}</p>
      )}
    </div>
  );
}

export default EntityPicker;
