"use client";

import AppShell from "../../../components/AppShell";

export default function InboundCampaignsPage() {
  return (
    <AppShell title="Inbound campaigns" subtitle="Reserved space for inbound journeys.">
      <section className="glass p-6 rounded-2xl">
        <p className="eyebrow">Inbound lane</p>
        <h2 className="text-xl font-semibold">This section is intentionally blank for now.</h2>
        <p className="muted text-sm">
          Add lead capture, handoffs, and nurture streams here when you are ready to design inbound flows.
        </p>
      </section>
    </AppShell>
  );
}
