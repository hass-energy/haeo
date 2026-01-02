/**
 * Card container component matching Home Assistant card styling.
 */

import "./Card.css";

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

function Card({ children, className = "" }: CardProps) {
  return <div className={`card ${className}`}>{children}</div>;
}

export default Card;
