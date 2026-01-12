"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
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

type SettingItem = {
  label: string;
  badge?: string;
};

type TopBarProps = {
  title: string;
  subtitle?: string;
  settingsOpen: boolean;
  onSettingsClick: () => void;
  onSignOut: () => void;
};

type SettingsDrawerProps = {
  options: SettingItem[];
  onClose: () => void;
};

const navItems: NavItem[] = [
  { label: "Home", href: "/crm", icon: "🏠" },
  { label: "Import CSVs", href: "/import", icon: "📥" },
  { label: "Email Generator", href: "/emails", icon: "✉️" },
  { label: "Leads", href: "/leads", icon: "👤" },
  { label: "Companies", href: "/companies", icon: "🏢" },
  { label: "Campaigns", href: "#", icon: "📣", soon: true },
  { label: "Reports", href: "/reports", icon: "📊" },
];

const SETTINGS_ITEMS: SettingItem[] = [
  { label: "Profile" },
  { label: "Organization" },
  { label: "Notifications" },
  { label: "Integrations" },
  { label: "Billing" },
  { label: "API Keys" },
  { label: "Appearance" },
  { label: "Security" },
  { label: "About" },
  { label: "Automations", badge: "Coming soon" },
  { label: "Channels", badge: "Coming soon" },
  { label: "Insights", badge: "Coming soon" },
  { label: "Activity", badge: "Coming soon" },
  { label: "Roadmap", badge: "Coming soon" },
  { label: "Support", badge: "Coming soon" },
  { label: "Feedback", badge: "Coming soon" },
];

export function AppShell({ title, subtitle, children }: AppShellProps) {
  const [expanded, setExpanded] = useState(false);
  const [authorized, setAuthorized] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const pathname = usePathname();

  const handleSignOut = () => {
    storage.clearToken();
    window.location.href = "/";
  };

  useEffect(() => {
    (async () => {
      const token = storage.getToken();

      const apiBase = storage.getApiBaseUrl().replace(/\/$/, "");
      try {
        const headers = token ? { Authorization: "Bearer " + token } : undefined;
        const res = await fetch(`${apiBase}/auth/me`, { headers });
        if (!res.ok) throw new Error("unauthorized");
        await res.json();
        setAuthorized(true);
      } catch {
        storage.clearToken();
        window.location.href = "/";
      }
    })();
  }, []);

  useEffect(() => {
    if (!settingsOpen) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSettingsOpen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [settingsOpen]);

  if (!authorized) {
    return null;
  }

  return (
    <div className={`app-shell ${expanded ? "is-expanded" : ""}`}>
      <aside className={`sidebar ${expanded ? "expanded" : ""}`}>
        <div className="sidebar__brand">
          <button className="sidebar__toggle" onClick={() => setExpanded((x) => !x)} aria-label="Toggle menu">
           ☰
          </button>
          <div className="sidebar__logo">
            <Image src="/copper.png" alt="Copper" width={40} height={40} />
            {expanded && <span className="sidebar__name">Copper CRM</span>}
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
            <span className="icon">🚪</span>
            {expanded && <span className="label">Sign out</span>}
          </button>
        </div>
      </aside>

      <div className="app-main">
        <TopBar
          title={title}
          subtitle={subtitle}
          settingsOpen={settingsOpen}
          onSettingsClick={() => setSettingsOpen((prev) => !prev)}
          onSignOut={handleSignOut}
        />
        <div className="app-inner">
          <div className="app-content">{children}</div>
        </div>
      </div>

      {settingsOpen && <SettingsDrawer options={SETTINGS_ITEMS} onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}

function TopBar({ title, subtitle, settingsOpen, onSettingsClick, onSignOut }: TopBarProps) {
  return (
    <div className="top-bar">
      <div className="top-bar__copy">
        <div>
          <p className="eyebrow">Copper CRM</p>
          <h1>{title}</h1>
          {subtitle && <p className="muted top-bar__subtitle">{subtitle}</p>}
        </div>
      </div>
      <div className="top-bar__actions">
        <button className="ghost-btn top-bar__signout" onClick={onSignOut}>
          Sign out
        </button>
        <button
          className="gear-btn"
          type="button"
          onClick={onSettingsClick}
          aria-label={`${settingsOpen ? "Close" : "Open"} settings`}
          aria-expanded={settingsOpen}
        >
          <span aria-hidden="true">⚙️</span>
        </button>
      </div>
    </div>
  );
}

function SettingsDrawer({ options, onClose }: SettingsDrawerProps) {
  return (
    <>
      <div className="settings-drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <aside
        className="settings-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-drawer-title"
      >
        <div className="settings-drawer__header">
          <div>
            <p className="eyebrow">Workspace</p>
            <h2 id="settings-drawer-title">Settings</h2>
          </div>
          <button className="settings-drawer__close" type="button" onClick={onClose} aria-label="Close settings">
            ×
          </button>
        </div>
        <div className="settings-drawer__list">
          {options.map((option) => (
            <button key={option.label} className="settings-drawer__item" type="button">
              <span>{option.label}</span>
              {option.badge && <span className="pill pill-muted">{option.badge}</span>}
            </button>
          ))}
        </div>
      </aside>
    </>
  );
}

export default AppShell;
