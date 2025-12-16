"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { storage } from "../lib/storage";

type AppShellProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

type NavItem = {
  label: string;
  href: string;
  icon: string;
  soon?: boolean;
};

const navItems: NavItem[] = [
  { label: "Home", href: "/crm", icon: "🏠" },
  { label: "Import CSVs", href: "/import", icon: "📥" },
  { label: "Leads", href: "#", icon: "👥", soon: true },
  { label: "Accounts", href: "#", icon: "🏢", soon: true },
  { label: "Reports", href: "#", icon: "📊", soon: true },
];

export function AppShell({ title, subtitle, children }: AppShellProps) {
  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();

  const handleSignOut = () => {
    storage.clearToken();
    window.location.href = "/";
  };

  return (
    <div className={`app-shell ${expanded ? "is-expanded" : ""}`}>
      <aside className={`sidebar ${expanded ? "expanded" : ""}`}>
        <div className="sidebar__brand">
          <button className="sidebar__toggle" onClick={() => setExpanded((x) => !x)} aria-label="Toggle menu">
            ☰
          </button>
          <div className="sidebar__logo">
            <Image src="/copper.png" alt="Copper" width={40} height={40} />
            {expanded && <span className="sidebar__name">Copper</span>}
          </div>
        </div>

        <nav className="sidebar__nav">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            if (item.soon) {
              return (
                <div key={item.label} className="sidebar__link disabled">
                  <span className="icon">{item.icon}</span>
                  {expanded && (
                    <span className="label">
                      {item.label} <span className="pill pill-muted">Soon</span>
                    </span>
                  )}
                </div>
              );
            }
            return (
              <Link key={item.label} href={item.href} className={`sidebar__link ${isActive ? "active" : ""}`}>
                <span className="icon">{item.icon}</span>
                {expanded && <span className="label">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar__footer">
          <button className="sidebar__signout" onClick={handleSignOut}>
            <span className="icon">↩</span>
            {expanded && <span className="label">Sign out</span>}
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-header">
          <div>
            <p className="eyebrow">Copper CRM</p>
            <h1>{title}</h1>
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          <div className="header-actions">
            <button className="ghost-btn" onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        </header>
        <div className="app-content">{children}</div>
      </div>
    </div>
  );
}

export default AppShell;
