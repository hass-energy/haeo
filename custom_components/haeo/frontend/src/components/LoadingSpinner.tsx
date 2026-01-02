/**
 * Loading spinner component.
 */

import "./LoadingSpinner.css";

interface LoadingSpinnerProps {
  message?: string;
}

function LoadingSpinner({ message = "Loading..." }: LoadingSpinnerProps) {
  return (
    <div className="loading-spinner">
      <div className="loading-spinner__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray="31.4 31.4"
          />
        </svg>
      </div>
      <p className="loading-spinner__message">{message}</p>
    </div>
  );
}

export default LoadingSpinner;
