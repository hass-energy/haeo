/**
 * Reusable form field component.
 */

import { useId } from "react";
import "./FormField.css";

interface SelectOption {
  value: string;
  label: string;
}

interface FormFieldProps {
  id: string;
  label: string;
  type?: "text" | "number" | "select" | "checkbox" | "entity";
  value: string | number | boolean | string[];
  onChange: (value: string | number | boolean | string[]) => void;
  placeholder?: string;
  description?: string;
  required?: boolean;
  disabled?: boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: SelectOption[];
  error?: string;
}

function FormField({
  id,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  description,
  required = false,
  disabled = false,
  min,
  max,
  step,
  options = [],
  error,
}: FormFieldProps) {
  const descriptionId = useId();
  const errorId = useId();

  const describedBy = [
    description ? descriptionId : null,
    error ? errorId : null,
  ]
    .filter(Boolean)
    .join(" ");

  if (type === "checkbox") {
    return (
      <div className="form-field form-field--checkbox">
        <label className="form-field__checkbox-label">
          <input
            type="checkbox"
            id={id}
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
            disabled={disabled}
            aria-describedby={describedBy || undefined}
          />
          <span className="form-field__checkbox-text">{label}</span>
        </label>
        {description && (
          <p id={descriptionId} className="form-field__description">
            {description}
          </p>
        )}
      </div>
    );
  }

  if (type === "select") {
    return (
      <div className="form-field">
        <label htmlFor={id} className="form-field__label">
          {label}
          {required && <span className="form-field__required">*</span>}
        </label>
        <select
          id={id}
          value={String(value)}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          required={required}
          className={`form-field__select ${error ? "form-field__select--error" : ""}`}
          aria-describedby={describedBy || undefined}
          aria-invalid={error ? "true" : undefined}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {description && (
          <p id={descriptionId} className="form-field__description">
            {description}
          </p>
        )}
        {error && (
          <p id={errorId} className="form-field__error" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="form-field">
      <label htmlFor={id} className="form-field__label">
        {label}
        {required && <span className="form-field__required">*</span>}
      </label>
      <input
        type={type}
        id={id}
        value={String(value)}
        onChange={(e) =>
          onChange(type === "number" ? Number(e.target.value) : e.target.value)
        }
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        min={min}
        max={max}
        step={step}
        className={`form-field__input ${error ? "form-field__input--error" : ""}`}
        aria-describedby={describedBy || undefined}
        aria-invalid={error ? "true" : undefined}
      />
      {description && (
        <p id={descriptionId} className="form-field__description">
          {description}
        </p>
      )}
      {error && (
        <p id={errorId} className="form-field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export default FormField;
