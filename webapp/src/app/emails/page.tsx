"use client";

import { useEffect, useState } from "react";
import AppShell from "../../components/AppShell";
import { storage } from "../../lib/storage";

type EmailStats = {
  pending: number;
  generated: number;
  average_cost_usd: number;
  estimated_total_cost_usd: number;
  model: string;
  sample_size: number;
};

type GenerateResponse = {
  attempted: number;
  generated: number;
  pending_after: number;
  total_cost_usd: number | null;
  model: string;
  errors: string[];
};

export default function EmailGeneratorPage() {
  const [apiBase, setApiBase] = useState<string>(() =>
    (process.env.NEXT_PUBLIC_API_BASE || storage.getApiBaseUrl() || "http://127.0.0.1:8000").replace(
      /\/$/,
      "",
    ),
  );

  const [stats, setStats] = useState<EmailStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [count, setCount] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>("Pick how many leads to generate for.");
  const [lastRun, setLastRun] = useState<GenerateResponse | null>(null);

  const pending = stats?.pending ?? 0;
  const selected = Math.min(count ?? pending, pending || 0);
  const estimatedCost = stats ? (stats.average_cost_usd || 0) * (selected || 0) : 0;

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const token = storage.getToken();
      if (!token) {
        window.location.href = "/";
        return;
      }

      const res = await fetch(`${apiBase}/first-emails/stats`, {
        headers: { Authorization: "Bearer " + token },
      });
      if (res.status === 401) {
        storage.clearToken();
        window.location.href = "/";
        return;
      }
      const data = await res.json();
      setStats(data);
    } catch (e: any) {
      setMessage(`Failed to load stats from ${apiBase}: ${e?.message || e}`);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const startGeneration = async (useAll: boolean) => {
    if (!stats) return;
    const token = storage.getToken();
    if (!token) {
      window.location.href = "/";
      return;
    }

    const targetCount = useAll ? undefined : count;
    if (!useAll && (!targetCount || targetCount <= 0)) {
      setMessage("Enter how many leads to generate.");
      return;
    }

    setBusy(true);
    setMessage("Starting generation...");

    try {
      const res = await fetch(`${apiBase}/first-emails/generate`, {
        method: "POST",
        headers: {
          Authorization: "Bearer " + token,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(targetCount ? { count: targetCount } : {}),
      });
      const data = await res.json();
      setLastRun(data);

      if (res.ok) {
        setMessage(
          `Generated ${data.generated}/${data.attempted} emails${
            data.total_cost_usd ? ` (est. $${data.total_cost_usd.toFixed(4)})` : ""
          }.`,
        );
      } else {
        setMessage(data?.detail || "Generation failed.");
      }
      await fetchStats();
    } catch (e: any) {
      setMessage(`Generation failed calling ${apiBase}: ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell title="AI Email Generator" subtitle="Generate first-touch emails for unmessaged leads.">
      <section className="glass rounded-2xl p-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-white/5 bg-black/10 p-4">
            <p className="eyebrow">Pending</p>
            <p className="text-3xl font-semibold">{loadingStats ? "…" : pending}</p>
            <p className="muted text-sm">Leads without a first email.</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-black/10 p-4">
            <p className="eyebrow">Generated</p>
            <p className="text-3xl font-semibold">{loadingStats ? "…" : stats?.generated ?? 0}</p>
            <p className="muted text-sm">Emails already created and stored.</p>
          </div>
          <div className="rounded-xl border border-white/5 bg-black/10 p-4">
            <p className="eyebrow">Est. Total</p>
            <p className="text-3xl font-semibold">
              {loadingStats ? "…" : `$${(stats?.estimated_total_cost_usd ?? 0).toFixed(4)}`}
            </p>
            <p className="muted text-sm">
              Based on {stats?.sample_size || 0 ? `${stats?.sample_size} samples` : "model pricing"}.
            </p>
          </div>
        </div>
      </section>

      <section className="glass rounded-2xl p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex-1 space-y-3">
            <p className="eyebrow">Generation target</p>
            <h2 className="text-xl font-semibold">Choose how many leads to generate emails for.</h2>
            <p className="muted text-sm">
              Use a smaller batch first if you want to review the copy before sending.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2">
                <span className="text-sm text-slate-200">Count</span>
                <input
                  type="number"
                  min={1}
                  max={pending || undefined}
                  value={count ?? ""}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (Number.isNaN(val) || val <= 0) {
                      setCount(null);
                    } else {
                      const max = pending || val;
                      setCount(Math.min(val, max));
                    }
                  }}
                  className="w-28 rounded-md border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white focus:border-copper-400 focus:outline-none"
                  placeholder={pending ? `Up to ${pending}` : "0"}
                />
              </label>

              <button
                onClick={() => setCount(pending || 0)}
                disabled={!pending || busy}
                className="btn ghost"
              >
                Use all pending
              </button>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                disabled={busy || !pending}
                className="btn primary"
                onClick={() => startGeneration(false)}
              >
                {busy ? "Generating…" : "Generate selected"}
              </button>
              <button
                disabled={busy || !pending}
                className="btn subtle"
                onClick={() => startGeneration(true)}
              >
                {busy ? "Working…" : "Generate all"}
              </button>
            </div>
            <p className="text-sm text-slate-300">{message}</p>
          </div>

          <div className="w-full max-w-sm space-y-3 rounded-xl border border-white/10 bg-black/30 p-4">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-slate-100">Estimate</p>
              <span className="pill pill-muted text-xs">Model: {stats?.model || "gpt-4o-mini"}</span>
            </div>
            <div className="flex items-end justify-between">
              <div>
                <p className="muted text-xs">For this batch</p>
                <p className="text-3xl font-semibold">${estimatedCost.toFixed(4)}</p>
              </div>
              <div className="text-right">
                <p className="muted text-xs">Avg / email</p>
                <p className="text-lg font-semibold">
                  ${stats ? (stats.average_cost_usd || 0).toFixed(4) : "0.0000"}
                </p>
              </div>
            </div>
            <p className="muted text-xs">
              Estimates come from prior runs{stats?.sample_size ? ` (${stats.sample_size} samples)` : ""} or
              model pricing. Actual OpenAI usage is saved with each generated email.
            </p>
          </div>
        </div>
      </section>

      <section className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Last run</h3>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span>API: {apiBase}</span>
            <button
              className="btn subtle text-xs"
              onClick={() => {
                const local = "http://127.0.0.1:8000";
                storage.setApiBaseUrl(local);
                setApiBase(local);
                setMessage(`API base set to ${local}. Reloading stats...`);
                fetchStats();
              }}
              disabled={busy}
            >
              Use local
            </button>
          </div>
          <button
            className="btn subtle text-sm"
            onClick={() => fetchStats()}
            disabled={busy}
          >
            Refresh stats
          </button>
        </div>
        {lastRun ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatChip label="Attempted" value={lastRun.attempted} />
            <StatChip label="Generated" value={lastRun.generated} />
            <StatChip label="Pending now" value={lastRun.pending_after} />
            <StatChip
              label="Cost"
              value={lastRun.total_cost_usd ? `$${lastRun.total_cost_usd.toFixed(4)}` : "n/a"}
            />
          </div>
        ) : (
          <p className="muted text-sm mt-2">No generation run yet.</p>
        )}
        {lastRun?.errors?.length ? (
          <div className="mt-4 rounded-lg border border-white/10 bg-red-950/40 p-3">
            <p className="font-semibold text-red-200">Errors</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-red-100">
              {lastRun.errors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    </AppShell>
  );
}

function StatChip({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/20 p-3">
      <p className="muted text-xs">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}
