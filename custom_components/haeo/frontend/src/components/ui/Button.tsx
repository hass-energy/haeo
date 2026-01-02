/**
 * Reusable button component.
 */

import "./Button.css";

interface ButtonProps {
  type?: "button" | "submit" | "reset";
  variant?: "primary" | "secondary" | "danger" | "text";
  size?: "small" | "medium" | "large";
  loading?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
  className?: string;
}

function Button({
  type = "button",
  variant = "secondary",
  size = "medium",
  loading = false,
  disabled = false,
  onClick,
  children,
  className = "",
}: ButtonProps) {
  const classNames = [
    "button",
    `button--${variant}`,
    `button--${size}`,
    loading ? "button--loading" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type={type}
      className={classNames}
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading}
    >
      {loading && <span className="button__spinner" aria-hidden="true" />}
      <span className={loading ? "button__content--hidden" : ""}>
        {children}
      </span>
    </button>
  );
}

export default Button;
