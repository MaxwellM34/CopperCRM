"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";
import { storage } from "../../../lib/storage";

type StepForm = {
  id?: number | null;
  title: string;
  step_type: string;
  sequence: number;
  lane?: string | null;
  position_x?: number | null;
  position_y?: number | null;
  prompt_template?: string | null;
  config: Record<string, any>;
  configText?: string;
};

type Campaign = {
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
  steps: StepForm[];
};

type LLMProfile = {
  id: number;
  name: string;
  description?: string | null;
  rules: string;
  is_default: boolean;
};

export default function CampaignEditorPage({ params }: { params: { id: string } }) {
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [steps, setSteps] = useState<StepForm[]>([]);
  const [llmProfiles, setLlmProfiles] = useState<LLMProfile[]>([]);
  const [saving, setSaving] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [launchNotes, setLaunchNotes] = useState<string>("");
  const [launchAudience, setLaunchAudience] = useState<number | null>(null);

  const apiBase = useMemo(() => storage.getApiBaseUrl().replace(/\/$/, ""), []);

  const loadCampaign = async () => {
    setError("");
    setMessage("Loading campaign...");
    try {
      const token = storage.getToken();
      const res = await fetch(`${apiBase}/campaigns/${params.id}`, {
        headers: token ? { Authorization: "Bearer " + token } : {},
      });
      if (res.status === 401) {
        window.location.href = "/";
        return;
      }
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to load campaign");
      }
      const mappedSteps: StepForm[] = (data.steps || []).map((step: any) => ({
        ...step,
        config: step.config || {},
        configText: JSON.stringify(step.config || {}, null, 2),
      }));
      setCampaign({ ...data, steps: mappedSteps });
      setSteps(mappedSteps);
      setLaunchNotes(data.launch_notes || "");
      setLaunchAudience(data.audience_size ?? null);
      setMessage("Loaded.");
    } catch (err: any) {
      setError(err?.message || "Failed to load campaign");
    }
  };

  const loadPreset = async () => {
    setMessage("Loading drip preset...");
    try {
      const token = storage.getToken();
      const res = await fetch(`${apiBase}/campaigns/presets/drip`, {
        headers: token ? { Authorization: "Bearer " + token } : {},
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to load preset");
      }
      const mappedSteps: StepForm[] = (data.steps || []).map((step: any) => ({
        ...step,
        config: step.config || {},
        configText: JSON.stringify(step.config || {}, null, 2),
      }));
      setSteps(mappedSteps);
      setCampaign((prev) =>
        prev
          ? {
              ...prev,
              description: data.description,
              ai_brief: data.ai_brief,
              preset_key: data.preset_key,
              steps: mappedSteps,
            }
          : prev,
      );
      setMessage("Preset loaded into editor. Save to persist.");
    } catch (err: any) {
      setError(err?.message || "Failed to load preset");
    }
  };

  const loadLlmProfiles = async () => {
    try {
      const token = storage.getToken();
      const res = await fetch(`${apiBase}/campaigns/llm-profiles`, {
        headers: token ? { Authorization: "Bearer " + token } : {},
      });
      const data = await res.json();
      if (Array.isArray(data)) {
        setLlmProfiles(data);
      }
    } catch {
      // ignore for now
    }
  };

  useEffect(() => {
    loadCampaign();
    loadLlmProfiles();
  }, []);

  const updateStep = (index: number, patch: Partial<StepForm>) => {
    setSteps((prev) => prev.map((step, i) => (i === index ? { ...step, ...patch } : step)));
  };

  const addStep = () => {
    setSteps((prev) => [
      ...prev,
      {
        title: "New step",
        step_type: "ai_email",
        sequence: prev.length + 1,
        lane: "Touches",
        prompt_template: "",
        config: {},
        configText: "{}",
      },
    ]);
  };

  const removeStep = (index: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== index));
  };

  const saveCampaign = async () => {
    if (!campaign) return;
    setSaving(true);
    setMessage("Saving...");
    setError("");
    try {
      const parsedSteps = steps.map((step) => {
        let parsedConfig: Record<string, any> = {};
        if (step.configText && step.configText.trim()) {
          try {
            parsedConfig = JSON.parse(step.configText);
          } catch (e: any) {
            throw new Error(`Step "${step.title}" has invalid JSON config: ${e?.message || e}`);
          }
        }
        return {
          title: step.title,
          step_type: step.step_type,
          sequence: step.sequence,
          lane: step.lane,
          position_x: step.position_x,
          position_y: step.position_y,
          prompt_template: step.prompt_template,
          config: parsedConfig,
        };
      });

      const token = storage.getToken();
      const body = {
        name: campaign.name,
        description: campaign.description,
        category: campaign.category,
        status: campaign.status,
        preset_key: campaign.preset_key,
        audience_size: campaign.audience_size,
        entry_point: campaign.entry_point,
        ai_brief: campaign.ai_brief,
        launch_notes: campaign.launch_notes,
        llm_profile_id: campaign.llm_profile_id,
        steps: parsedSteps,
      };

      const res = await fetch(`${apiBase}/campaigns/${campaign.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: "Bearer " + token } : {}),
        },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to save campaign");
      }
      const mappedSteps: StepForm[] = (data.steps || []).map((step: any) => ({
        ...step,
        config: step.config || {},
        configText: JSON.stringify(step.config || {}, null, 2),
      }));
      setCampaign({ ...data, steps: mappedSteps });
      setSteps(mappedSteps);
      setMessage("Saved.");
    } catch (err: any) {
      setError(err?.message || "Failed to save campaign");
    } finally {
      setSaving(false);
    }
  };

  const launchCampaign = async () => {
    if (!campaign) return;
    setLaunching(true);
    setMessage("Launching...");
    setError("");
    try {
      const token = storage.getToken();
      const res = await fetch(`${apiBase}/campaigns/${campaign.id}/launch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: "Bearer " + token } : {}),
        },
        body: JSON.stringify({
          notes: launchNotes || undefined,
          audience_size: launchAudience ?? undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Launch failed");
      }
      setCampaign((prev) => (prev ? { ...prev, status: data.status, launched_at: data.launched_at } : prev));
      setMessage("Campaign launched.");
    } catch (err: any) {
      setError(err?.message || "Launch failed");
    } finally {
      setLaunching(false);
    }
  };

  const onFieldChange = (key: keyof Campaign, value: any) => {
    setCampaign((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  if (!campaign) {
    return (
      <AppShell title="Campaign editor" subtitle="Loading...">
        <p className="muted">{error || message || "Loading..."}</p>
      </AppShell>
    );
  }

  return (
    <AppShell title={`Campaign: ${campaign.name}`} subtitle="Full editor with prompts and LLM rules.">
      <section className="glass launch-panel">
        <div className="launch-panel__copy">
          <p className="eyebrow">Campaign info</p>
          <div className="editor-grid">
            <label className="launch-field">
              <span>Name</span>
              <input value={campaign.name} onChange={(e) => onFieldChange("name", e.target.value)} />
            </label>
            <label className="launch-field">
              <span>Status</span>
              <select value={campaign.status} onChange={(e) => onFieldChange("status", e.target.value)}>
                <option value="draft">Draft</option>
                <option value="launched">Launched</option>
                <option value="paused">Paused</option>
              </select>
            </label>
            <label className="launch-field">
              <span>Category</span>
              <input value={campaign.category} onChange={(e) => onFieldChange("category", e.target.value)} />
            </label>
            <label className="launch-field">
              <span>Audience size</span>
              <input
                type="number"
                value={campaign.audience_size ?? ""}
                onChange={(e) => onFieldChange("audience_size", e.target.value ? parseInt(e.target.value, 10) : null)}
              />
            </label>
            <label className="launch-field">
              <span>Entry point</span>
              <input
                value={campaign.entry_point ?? ""}
                onChange={(e) => onFieldChange("entry_point", e.target.value)}
              />
            </label>
            <label className="launch-field">
              <span>LLM rule set</span>
              <select
                value={campaign.llm_profile_id ?? ""}
                onChange={(e) =>
                  onFieldChange("llm_profile_id", e.target.value ? parseInt(e.target.value, 10) : null)
                }
              >
                <option value="">Default</option>
                {llmProfiles.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} {p.is_default ? "(default)" : ""}
                  </option>
                ))}
              </select>
              <small className="muted">
                Manage rule sets in <a href="/campaigns/llm-knowledge">LLM Knowledge</a>.
              </small>
            </label>
          </div>
          <label className="launch-field">
            <span>Description</span>
            <textarea
              value={campaign.description ?? ""}
              onChange={(e) => onFieldChange("description", e.target.value)}
            />
          </label>
          <label className="launch-field">
            <span>AI Brief</span>
            <textarea value={campaign.ai_brief ?? ""} onChange={(e) => onFieldChange("ai_brief", e.target.value)} />
          </label>
          <div className="launch-actions">
            <button className="btn primary" onClick={saveCampaign} disabled={saving}>
              {saving ? "Saving..." : "Save campaign"}
            </button>
            <button className="btn subtle" onClick={loadPreset}>
              Load drip preset
            </button>
            <button className="btn subtle" onClick={loadCampaign} disabled={saving}>
              Reset from API
            </button>
          </div>
          {message && <p className="muted text-xs">{message}</p>}
          {error && <p className="text-red-400 text-sm">{error}</p>}
        </div>

        <div className="launch-card">
          <div className="launch-card__meta">
            <span className="pill pill-muted text-xs">ID: {campaign.id}</span>
            <span className="pill pill-muted text-xs">{campaign.status}</span>
          </div>
          <p className="muted text-sm">Launch any time; this does not auto-send but marks the campaign ready.</p>
          <label className="launch-field">
            <span>Launch notes</span>
            <textarea value={launchNotes} onChange={(e) => setLaunchNotes(e.target.value)} />
          </label>
          <label className="launch-field">
            <span>Audience size for launch</span>
            <input
              type="number"
              value={launchAudience ?? ""}
              onChange={(e) => setLaunchAudience(e.target.value ? parseInt(e.target.value, 10) : null)}
            />
          </label>
          <div className="launch-actions">
            <button className="btn primary" onClick={launchCampaign} disabled={launching}>
              {launching ? "Launching..." : "Launch campaign"}
            </button>
          </div>
          {campaign.launched_at && (
            <span className="pill pill-muted text-xs">Launched at {new Date(campaign.launched_at).toLocaleString()}</span>
          )}
        </div>
      </section>

      <section className="glass campaign-board">
        <div className="campaign-board__header">
          <div>
            <p className="eyebrow">Steps and prompts</p>
            <h3>Edit every touch, wait, and logic block.</h3>
            <p className="muted text-sm">
              Config is JSON per step; prompts are editable text. Save to persist changes.
            </p>
          </div>
          <div className="campaign-meta">
            <button className="btn subtle" onClick={addStep}>
              Add step
            </button>
          </div>
        </div>

        <div className="flow-editor">
          {steps.map((step, idx) => (
            <div key={idx} className="flow-editor__step glass">
              <div className="flow-editor__header">
                <div className="flow-node__type">Step {idx + 1}</div>
                <div className="flow-editor__actions">
                  <button className="btn ghost text-xs" onClick={() => removeStep(idx)}>
                    Remove
                  </button>
                </div>
              </div>
              <div className="editor-grid">
                <label className="launch-field">
                  <span>Title</span>
                  <input value={step.title} onChange={(e) => updateStep(idx, { title: e.target.value })} />
                </label>
                <label className="launch-field">
                  <span>Type</span>
                  <select
                    value={step.step_type}
                    onChange={(e) => updateStep(idx, { step_type: e.target.value })}
                  >
                    <option value="entry">Entry</option>
                    <option value="ai_email">AI email</option>
                    <option value="delay">Delay</option>
                    <option value="ai_decision">AI decision</option>
                    <option value="goal">Goal</option>
                    <option value="exit">Exit</option>
                  </select>
                </label>
                <label className="launch-field">
                  <span>Sequence</span>
                  <input
                    type="number"
                    value={step.sequence}
                    onChange={(e) => updateStep(idx, { sequence: parseInt(e.target.value, 10) || 0 })}
                  />
                </label>
                <label className="launch-field">
                  <span>Lane</span>
                  <input value={step.lane ?? ""} onChange={(e) => updateStep(idx, { lane: e.target.value })} />
                </label>
              </div>
              <label className="launch-field">
                <span>Prompt (editable)</span>
                <textarea
                  value={step.prompt_template ?? ""}
                  onChange={(e) => updateStep(idx, { prompt_template: e.target.value })}
                />
              </label>
              <label className="launch-field">
                <span>Config (JSON)</span>
                <textarea
                  value={step.configText ?? ""}
                  onChange={(e) => updateStep(idx, { configText: e.target.value })}
                  className="code-textarea"
                  spellCheck={false}
                />
              </label>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
