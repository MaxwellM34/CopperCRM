"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";
import { storage } from "../../../lib/storage";

type CampaignStep = {
  id: number;
  title: string;
  step_type: string;
  sequence: number;
  lane?: string | null;
  position_x?: number | null;
  position_y?: number | null;
  config: Record<string, any>;
};

type Campaign = {
  id: number;
  name: string;
  description?: string | null;
  category: string;
  status: string;
  ai_brief?: string | null;
  audience_size?: number | null;
  launch_notes?: string | null;
  launched_at?: string | null;
  preset_key?: string | null;
  step_count?: number | null;
  steps: CampaignStep[];
};

export default function ColdOutboundCampaignPage() {
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string>("Loading campaign...");
  const [launchNotes, setLaunchNotes] = useState<string>("");
  const [audienceSize, setAudienceSize] = useState<number | null>(null);
  const [launching, setLaunching] = useState(false);
  const [apiBase, setApiBase] = useState<string>(() => storage.getApiBaseUrl().replace(/\/$/, ""));

  const orderedSteps = useMemo(() => {
    if (!campaign?.steps) return [];
    return [...campaign.steps].sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
  }, [campaign?.steps]);

  const logicStep = useMemo(
    () => orderedSteps.find((step) => step.step_type === "ai_decision"),
    [orderedSteps],
  );
  const logicRules = Array.isArray(logicStep?.config?.routing) ? logicStep?.config?.routing : [];

  const loadCampaign = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = storage.getToken();
      const base = storage.getApiBaseUrl().replace(/\/$/, "");
      setApiBase(base);
      const headers = token ? { Authorization: "Bearer " + token } : {};
      const listRes = await fetch(`${base}/campaigns`, { headers });
      if (listRes.status === 401) {
        window.location.href = "/";
        return;
      }
      const listData = await listRes.json();
      const target =
        (Array.isArray(listData) &&
          listData.find((c: Campaign) => c.category === "cold_outbound")) ||
        (Array.isArray(listData) ? listData[0] : null);
      if (!target?.id) {
        throw new Error("No campaign found. Create one first.");
      }

      const detailRes = await fetch(`${base}/campaigns/${target.id}`, { headers });
      const detail = await detailRes.json();
      if (!detailRes.ok) {
        throw new Error(detail?.detail || "Failed to load campaign");
      }
      setCampaign(detail);
      setAudienceSize(detail.audience_size ?? null);
      setLaunchNotes(detail.launch_notes || "");
      setStatusMsg(detail.status ? `Status: ${detail.status}` : "Ready to launch");
    } catch (err: any) {
      setError(err?.message || "Failed to load campaign");
      setStatusMsg("Unable to load the preset right now.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaign();
  }, []);

  const launchCampaign = async () => {
    if (!campaign) return;
    setLaunching(true);
    setStatusMsg("Launching...");
    try {
      const token = storage.getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = "Bearer " + token;
      }
      const res = await fetch(`${apiBase}/campaigns/${campaign.id}/launch`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          notes: launchNotes || undefined,
          audience_size: audienceSize ?? undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Launch failed");
      }
      setCampaign(data);
      setStatusMsg("Campaign launched and marked live.");
    } catch (err: any) {
      setError(err?.message || "Launch failed");
      setStatusMsg("Launch failed. Check API status.");
    } finally {
      setLaunching(false);
    }
  };

  const presetDescription =
    campaign?.ai_brief ||
    "AI-generated drips with automatic replies. If a prospect asks a question but is not ready to meet, the AI answers, keeps the thread warm, and re-asks for a call after a short exchange.";

  return (
    <AppShell
      title="Cold outbound campaigns"
      subtitle="Visual builder for the AI drip preset."
    >
      <section className="glass launch-panel">
        <div className="launch-panel__copy">
          <p className="eyebrow">Cold outbound preset</p>
          <h2 className="text-xl font-semibold">{campaign?.name || "AI cold outbound drip"}</h2>
          <p className="muted text-sm">
            {campaign?.description ||
              "Three-touch drip plus AI reply handling that stays in the thread until a meeting is booked."}
          </p>

          <div className="launch-form">
            <label className="launch-field">
              <span>Audience size</span>
              <input
                type="number"
                min={0}
                value={audienceSize ?? ""}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  setAudienceSize(Number.isNaN(val) ? null : val);
                }}
              />
            </label>
            <label className="launch-field">
              <span>Launch notes</span>
              <textarea
                value={launchNotes}
                onChange={(e) => setLaunchNotes(e.target.value)}
                placeholder="Add context for this launch or a link to the lead list."
              />
            </label>
          </div>

          <div className="launch-actions">
            <button className="btn primary" onClick={launchCampaign} disabled={launching || !campaign}>
              {launching ? "Launching..." : "Launch campaign"}
            </button>
            <button className="btn subtle" onClick={loadCampaign} disabled={loading}>
              Reload preset
            </button>
          </div>
          <p className="muted text-xs">{statusMsg}</p>
          {error && <p className="text-red-400 text-sm mt-1">{error}</p>}
        </div>

        <div className="launch-card">
          <div className="launch-card__meta">
            <span className="pill pill-muted text-xs">API: {apiBase}</span>
            <StatusPill status={campaign?.status || "draft"} />
          </div>
          <p className="muted text-sm">{presetDescription}</p>
          <ul className="launch-highlights">
            <li>AI writes each touch with lead + company context.</li>
            <li>Reply logic keeps talking until a meeting is booked.</li>
            <li>Unsubscribe or negative replies end the sequence instantly.</li>
          </ul>
          <div className="launch-card__footer">
            <span className="pill pill-muted text-xs">
              Steps: {campaign?.step_count ?? campaign?.steps?.length ?? 0}
            </span>
            {campaign?.launched_at && (
              <span className="pill pill-muted text-xs">
                Launched at {new Date(campaign.launched_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      </section>

      <section className="glass campaign-board">
        <div className="campaign-board__header">
          <div>
            <p className="eyebrow">Flow builder</p>
            <h3>AI drip visualization</h3>
            <p className="muted text-sm">
              Modeled after Mautic but simplified: touches, waits, AI reply router, and clear outcomes.
            </p>
          </div>
          <div className="campaign-meta">
            <StatusPill status={campaign?.status || "draft"} />
            <span className="pill pill-muted text-xs">
              Audience: {audienceSize ?? campaign?.audience_size ?? 0}
            </span>
          </div>
        </div>

        <div className="flow-canvas">
          {orderedSteps.length === 0 && <p className="muted">No steps yet.</p>}
          {orderedSteps.length > 0 && (
            <>
              <div className="flow-row">
                {orderedSteps.map((step, idx) => (
                  <Fragment key={step.id}>
                    <FlowNode step={step} />
                    {idx < orderedSteps.length - 1 && <div className="flow-connector" />}
                  </Fragment>
                ))}
              </div>
              {logicRules && logicRules.length > 0 && (
                <div className="flow-branch">
                  {logicRules.map((rule: Record<string, string>, idx: number) => (
                    <BranchCard key={idx} title={rule?.if || "Rule"} action={rule?.then || ""} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <div className="flow-legend">
          <div>
            <p className="eyebrow">Preset actions</p>
            <ul>
              <li>AI emails use role and industry details with short CTAs.</li>
              <li>Wait steps respect working hours to mimic real sending.</li>
              <li>
                Reply router answers questions, then nudges toward a meeting if the prospect has not booked yet.
              </li>
            </ul>
          </div>
          <div>
            <p className="eyebrow">Outcomes</p>
            <ul>
              <li>Meeting booked → notify owner and stop outreach.</li>
              <li>Warm but not ready → move to nurture.</li>
              <li>Negative → stop and mark do-not-contact.</li>
            </ul>
          </div>
        </div>
      </section>
    </AppShell>
  );
}

function FlowNode({ step }: { step: CampaignStep }) {
  const typeLabels: Record<string, string> = {
    entry: "Entry",
    ai_email: "AI email",
    delay: "Wait",
    ai_decision: "AI logic",
    goal: "Goal",
    exit: "Exit",
  };
  const label = typeLabels[step.step_type] || "Step";

  let summary = "";
  if (step.step_type === "ai_email") {
    summary = step.config?.cta || step.config?.tone || "AI generated email touch.";
  } else if (step.step_type === "delay") {
    summary = `Wait ${step.config?.duration_hours ?? "?"}h`;
  } else if (step.step_type === "ai_decision") {
    summary = "AI reads replies and routes to book, answer, or stop.";
  } else if (step.step_type === "goal") {
    summary = step.config?.action || "Goal: book meeting";
  } else if (step.step_type === "entry") {
    summary = step.config?.source || "Entry point";
  }

  const chips: string[] = [];
  if (step.config?.tone) chips.push(`Tone: ${step.config.tone}`);
  if (step.config?.ai_model) chips.push(`Model: ${step.config.ai_model}`);
  if (step.config?.cta && step.step_type === "ai_email") chips.push(step.config.cta);
  if (step.step_type === "delay" && step.config?.duration_hours) {
    chips.push(`${step.config.duration_hours} hours`);
  }
  if (step.step_type === "ai_decision" && step.config?.auto_continue) {
    chips.push("Auto-continue enabled");
  }

  return (
    <div className={`flow-node flow-node--${step.step_type}`}>
      <div className="flow-node__type">{label}</div>
      <h4 className="flow-node__title">{step.title}</h4>
      {summary && <p className="flow-node__summary">{summary}</p>}
      {chips.length > 0 && (
        <div className="flow-node__chips">
          {chips.map((chip, idx) => (
            <span key={idx} className="pill pill-muted text-xs">
              {chip}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function BranchCard({ title, action }: { title: string; action: string }) {
  return (
    <div className="flow-branch__card glass">
      <p className="eyebrow">If</p>
      <h4>{title}</h4>
      <p className="muted text-sm">Then {action}</p>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const normalized = (status || "draft").toLowerCase();
  const label = normalized.charAt(0).toUpperCase() + normalized.slice(1);
  return <span className={`status-pill status-${normalized}`}>{label}</span>;
}
