"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "../../components/AppShell";
import { storage } from "../../lib/storage";

type CampaignSummary = {
  id: number;
  name: string;
  description?: string | null;
  category: string;
  status: string;
  preset_key?: string | null;
  audience_size?: number | null;
  entry_point?: string | null;
  ai_brief?: string | null;
  launch_notes?: string | null;
  launched_at?: string | null;
  llm_profile_id?: number | null;
  llm_profile_name?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  step_count?: number;
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState<string>("Cold outbound (copy)");
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<string>("");

  const fetchCampaigns = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = storage.getToken();
      const apiBase = storage.getApiBaseUrl().replace(/\/$/, "");
      const res = await fetch(`${apiBase}/campaigns`, {
        headers: token ? { Authorization: "Bearer " + token } : {},
      });
      if (res.status === 401) {
        window.location.href = "/";
        return;
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        setCampaigns(data);
      } else {
        setCampaigns([]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load campaigns");
    } finally {
      setLoading(false);
    }
  };

  const createFromPreset = async () => {
    if (!newName.trim()) {
      setMessage("Enter a campaign name.");
      return;
    }
    setCreating(true);
    setMessage("Creating from drip preset...");
    try {
      const token = storage.getToken();
      const apiBase = storage.getApiBaseUrl().replace(/\/$/, "");
      const res = await fetch(`${apiBase}/campaigns`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: "Bearer " + token } : {}),
        },
        body: JSON.stringify({
          name: newName,
          preset_key: "ai_cold_outbound_drip",
          category: "cold_outbound",
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to create campaign");
      }
      setMessage("Campaign created from preset. Opening editor...");
      window.location.href = `/campaigns/${data.id}`;
    } catch (err: any) {
      setMessage(err?.message || "Failed to create campaign");
    } finally {
      setCreating(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  return (
    <AppShell
      title="Campaigns"
      subtitle="Full editing, presets, and AI rule sets for outreach journeys."
    >
      <section className="glass campaign-hero">
        <div>
          <p className="eyebrow">Pipeline renamed</p>
          <h2>Design campaigns with AI-managed replies.</h2>
          <p className="muted">
            Build and save campaigns, edit every AI prompt, and launch when ready. Use the default cold outbound
            drip as a starting point or craft your own.
          </p>
          <div className="campaign-actions">
            <Link href="/campaigns/llm-knowledge" className="btn subtle">
              LLM Knowledge rules
            </Link>
            <Link href="/campaigns/inbound" className="btn subtle">
              Inbound workspace
            </Link>
          </div>
        </div>
        <div className="glass" style={{ padding: "12px", borderRadius: "12px" }}>
          <p className="eyebrow">New campaign</p>
          <label className="launch-field" style={{ gap: "6px" }}>
            <span>Name</span>
            <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="My campaign copy" />
          </label>
          <button className="btn primary w-full" onClick={createFromPreset} disabled={creating}>
            {creating ? "Creating..." : "Create from drip preset"}
          </button>
          {message && <p className="muted text-xs mt-1">{message}</p>}
        </div>
      </section>

      <section className="campaign-grid">
        <CampaignCard
          title="Cold outbound"
          desc="Use the AI drip preset, edit prompts, and launch when ready."
          href="/campaigns/coldoutbound"
          badge="Preset ready"
        />
        <CampaignCard
          title="Inbound"
          desc="Reserve a lane for inbound nurtures or handoffs. Left intentionally blank for now."
          href="/campaigns/inbound"
          badge="Blank"
        />
        <CampaignCard
          title="LLM Knowledge"
          desc="Create and manage rule sets the AI uses across campaigns."
          href="/campaigns/llm-knowledge"
          badge="Rules"
        />
      </section>

      <section className="glass campaign-list">
        <div className="campaign-list__header">
          <div>
            <p className="eyebrow">Active drafts</p>
            <h3>Campaign roster</h3>
            <p className="muted text-sm">
              Seeded with an AI cold outbound drip. Edit any campaign and launch when ready.
            </p>
          </div>
          <button className="btn subtle text-sm" onClick={fetchCampaigns} disabled={loading}>
            Refresh
          </button>
        </div>

        {error && <p className="text-red-400">{error}</p>}
        {loading && <p className="muted">Loading campaigns...</p>}
        {!loading && !error && campaigns.length === 0 && <p className="muted">No campaigns yet.</p>}

        {!loading && !error && campaigns.length > 0 && (
          <div className="campaign-table">
            {campaigns.map((c) => (
              <div key={c.id} className="campaign-row">
                <div className="campaign-row__main">
                  <div>
                    <div className="campaign-row__title">
                      <Link href={`/campaigns/${c.id ?? ""}`}>{c.name}</Link>
                      <StatusPill status={c.status} />
                    </div>
                    <p className="muted text-sm">{c.description || "No description yet."}</p>
                  </div>
                  <div className="campaign-row__meta">
                    <span className="pill pill-muted text-xs">{c.category}</span>
                    <span className="pill pill-muted text-xs">{c.step_count || 0} steps</span>
                    {c.preset_key && <span className="pill pill-muted text-xs">Preset</span>}
                    {c.llm_profile_name && <span className="pill pill-muted text-xs">LLM: {c.llm_profile_name}</span>}
                  </div>
                </div>
                <div className="campaign-row__actions">
                  <Link href={`/campaigns/${c.id ?? ""}`} className="btn subtle text-sm">
                    Edit
                  </Link>
                  <Link href="/campaigns/coldoutbound" className="btn ghost text-sm">
                    Visualize
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}

function CampaignCard({
  title,
  desc,
  href,
  badge,
}: {
  title: string;
  desc: string;
  href: string;
  badge?: string;
}) {
  return (
    <Link href={href} className="campaign-card glass">
      <div className="campaign-card__header">
        <h3>{title}</h3>
        {badge && <span className="pill pill-muted text-xs">{badge}</span>}
      </div>
      <p className="muted text-sm">{desc}</p>
      <span className="link-arrow">Open</span>
    </Link>
  );
}

function StatusPill({ status }: { status: string }) {
  const normalized = (status || "draft").toLowerCase();
  const label = normalized.charAt(0).toUpperCase() + normalized.slice(1);
  return <span className={`status-pill status-${normalized}`}>{label}</span>;
}
