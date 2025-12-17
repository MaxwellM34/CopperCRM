"use client";

import Image from "next/image";
import Link from "next/link";
import AppShell from "../../components/AppShell";

const tiles = [
  {
    title: "Import CSVs",
    desc: "Upload spreadsheets to create leads and companies.",
    href: "/import",
    cta: "Start import",
  },
  {
    title: "AI Emails",
    desc: "Generate or approve first-touch emails.",
    href: "/emails",
    cta: "Open AI emails",
  },
  {
    title: "Leads",
    desc: "View and score your leads. Coming soon.",
    href: "#",
    soon: true,
  },
  {
    title: "Accounts",
    desc: "Manage company records. Coming soon.",
    href: "#",
    soon: true,
  },
  {
    title: "Reports",
    desc: "Pipeline and activity insights. Coming soon.",
    href: "#",
    soon: true,
  },
];

export default function CrmHome() {
  return (
    <AppShell title="Home" subtitle="Jump into your CRM tools.">
      <section className="crm-hero glass">
        <div className="crm-hero__copy">
          <p className="eyebrow">Welcome back</p>
          <h2>Everything starts here.</h2>
          <p className="muted">CRM simplified by Dr. Copper.</p>
          <div className="actions">
            <Link href="/import" className="btn primary">Go to Imports</Link>
            <button className="btn ghost" onClick={() => window.scrollTo({ top: 500, behavior: "smooth" })}>
              Browse sections
            </button>
          </div>
        </div>
        <div className="crm-hero__art">
          <Image src="/copper.png" alt="Copper mascot" width={200} height={200} className="hero-img" />
        </div>
      </section>

      <section className="tile-grid">
        {tiles.map((tile) => (
          <div key={tile.title} className="tile glass">
            <div className="tile__header">
              <h3>{tile.title}</h3>
              {tile.soon && <span className="pill pill-muted">Soon</span>}
            </div>
            <p className="muted">{tile.desc}</p>
            <div className="tile__actions">
              {tile.soon ? (
                <button className="btn ghost" disabled>
                  Coming soon
                </button>
              ) : (
                <Link href={tile.href} className="btn subtle">
                  {tile.cta || "Open"}
                </Link>
              )}
            </div>
          </div>
        ))}
      </section>
    </AppShell>
  );
}
