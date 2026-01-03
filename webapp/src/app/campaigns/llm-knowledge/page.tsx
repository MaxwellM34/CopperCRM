"use client";

import { useEffect, useState } from "react";
import AppShell from "../../../components/AppShell";
import { storage } from "../../../lib/storage";

type LLMProfile = {
  id: number;
  name: string;
  description?: string | null;
  rules: string;
  is_default: boolean;
};

export default function LlmKnowledgePage() {
  const [profiles, setProfiles] = useState<LLMProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [message, setMessage] = useState<string>("");

  const [newProfile, setNewProfile] = useState({
    name: "Base LLM Rules",
    description: "Default context used across campaigns.",
    rules: "",
    is_default: false,
  });

  const apiBase = storage.getApiBaseUrl().replace(/\/$/, "");

  const fetchProfiles = async () => {
    setLoading(true);
    setError("");
    try {
      const token = storage.getToken();
      const res = await fetch(`${apiBase}/campaigns/llm-profiles`, {
        headers: token ? { Authorization: "Bearer " + token } : {},
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to load profiles");
      setProfiles(data || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load profiles");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfiles();
  }, []);

  const createProfile = async () => {
    setMessage("Creating profile...");
    setError("");
    try {
      const token = storage.getToken();
      const res = await fetch(`${apiBase}/campaigns/llm-profiles`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: "Bearer " + token } : {}),
        },
        body: JSON.stringify(newProfile),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to create profile");
      setMessage("Profile created.");
      setNewProfile({ name: "New profile", description: "", rules: "", is_default: false });
      fetchProfiles();
    } catch (err: any) {
      setError(err?.message || "Failed to create profile");
    }
  };

  const updateProfile = async (profile: LLMProfile) => {
    setMessage(`Updating ${profile.name}...`);
    setError("");
    try {
      const token = storage.getToken();
      const res = await fetch(`${apiBase}/campaigns/llm-profiles/${profile.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: "Bearer " + token } : {}),
        },
        body: JSON.stringify(profile),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to update profile");
      setMessage("Updated.");
      fetchProfiles();
    } catch (err: any) {
      setError(err?.message || "Failed to update profile");
    }
  };

  const setDefault = async (profile: LLMProfile) => {
    await updateProfile({ ...profile, is_default: true });
  };

  return (
    <AppShell title="LLM Knowledge" subtitle="Rule sets the AI uses across campaigns.">
      <section className="glass p-4 rounded-2xl">
        <p className="eyebrow">Create rule set</p>
        <div className="editor-grid">
          <label className="launch-field">
            <span>Name</span>
            <input value={newProfile.name} onChange={(e) => setNewProfile({ ...newProfile, name: e.target.value })} />
          </label>
          <label className="launch-field">
            <span>Description</span>
            <input
              value={newProfile.description}
              onChange={(e) => setNewProfile({ ...newProfile, description: e.target.value })}
            />
          </label>
          <label className="launch-field">
            <span>Rules (prompt content)</span>
            <textarea
              value={newProfile.rules}
              onChange={(e) => setNewProfile({ ...newProfile, rules: e.target.value })}
              rows={5}
            />
          </label>
          <label className="launch-field">
            <span>Set as default</span>
            <input
              type="checkbox"
              checked={newProfile.is_default}
              onChange={(e) => setNewProfile({ ...newProfile, is_default: e.target.checked })}
            />
          </label>
        </div>
        <button className="btn primary mt-2" onClick={createProfile}>
          Create rule set
        </button>
      </section>

      <section className="glass campaign-list">
        <div className="campaign-list__header">
          <div>
            <p className="eyebrow">Existing rule sets</p>
            <h3>LLM profiles</h3>
          </div>
          <button className="btn subtle text-sm" onClick={fetchProfiles} disabled={loading}>
            Refresh
          </button>
        </div>
        {message && <p className="muted text-xs">{message}</p>}
        {error && <p className="text-red-400 text-sm">{error}</p>}
        {loading && <p className="muted text-sm">Loading...</p>}
        {!loading && profiles.length === 0 && <p className="muted">No profiles yet.</p>}

        <div className="flow-editor">
          {profiles.map((p) => (
            <div key={p.id} className="flow-editor__step glass">
              <div className="flow-editor__header">
                <div className="flow-node__type">
                  {p.name} {p.is_default ? "(default)" : ""}
                </div>
                {!p.is_default && (
                  <button className="btn ghost text-xs" onClick={() => setDefault(p)}>
                    Set default
                  </button>
                )}
              </div>
              <label className="launch-field">
                <span>Name</span>
                <input
                  value={p.name}
                  onChange={(e) => setProfiles((prev) => prev.map((x) => (x.id === p.id ? { ...x, name: e.target.value } : x)))}
                />
              </label>
              <label className="launch-field">
                <span>Description</span>
                <input
                  value={p.description ?? ""}
                  onChange={(e) =>
                    setProfiles((prev) => prev.map((x) => (x.id === p.id ? { ...x, description: e.target.value } : x)))
                  }
                />
              </label>
              <label className="launch-field">
                <span>Rules</span>
                <textarea
                  value={p.rules}
                  onChange={(e) =>
                    setProfiles((prev) => prev.map((x) => (x.id === p.id ? { ...x, rules: e.target.value } : x)))
                  }
                  rows={6}
                />
              </label>
              <div className="launch-actions">
                <button className="btn primary text-sm" onClick={() => updateProfile(p)}>
                  Save changes
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
