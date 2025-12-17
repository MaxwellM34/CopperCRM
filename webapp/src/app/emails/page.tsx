"use client";

import Link from "next/link";
import AppShell from "../../components/AppShell";

export default function EmailsHome() {
  return (
    <AppShell title="AI Emails" subtitle="Generate or approve first-touch emails.">
      <section className="glass rounded-2xl p-6 space-y-3">
        <h2 className="text-xl font-semibold">Pick a workflow</h2>
        <p className="muted text-sm">
          Generate fresh emails for pending leads or swipe through existing drafts to approve/reject them.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          <Card
            title="Generate emails"
            desc="Create new first-touch emails for leads without outreach."
            cta="Open generator"
            href="/emails/generate"
          />
          <Card
            title="Approve emails"
            desc="Swipe right/left on drafted emails to mark human approval."
            cta="Start swiping"
            href="/emails/approve"
          />
        </div>
      </section>
    </AppShell>
  );
}

function Card({ title, desc, cta, href }: { title: string; desc: string; cta: string; href: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-5 flex flex-col gap-3">
      <div>
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="muted text-sm">{desc}</p>
      </div>
      <div>
        <Link href={href} className="btn primary">
          {cta}
        </Link>
      </div>
    </div>
  );
}
