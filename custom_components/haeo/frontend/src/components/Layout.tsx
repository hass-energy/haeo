/**
 * Main layout wrapper component.
 */

import type { ReactNode } from "react";
import "./Layout.css";

interface LayoutProps {
  children: ReactNode;
}

function Layout({ children }: LayoutProps) {
  return (
    <div className="layout">
      <header className="layout__header">
        <h1 className="layout__title">HAEO Configuration</h1>
      </header>
      <main className="layout__main">{children}</main>
    </div>
  );
}

export default Layout;
