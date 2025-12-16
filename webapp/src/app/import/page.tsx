"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { storage } from "../../lib/storage";

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE ||
  storage.getApiBaseUrl() ||
  "http://127.0.0.1:8000";

export default function ImportPage() {
  const [status, setStatus] = useState<string>("Choose a CSV to upload.");
  const [busy, setBusy] = useState(false);
  const responseRef = useRef<HTMLPreElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [tokenOk, setTokenOk] = useState<boolean>(false);

  useEffect(() => {
    const token = storage.getToken();
    setTokenOk(Boolean(token));
  }, []);

  const handleUpload = async () => {
    const token = storage.getToken();
    if (!token) {
      setStatus("Please sign in again.");
      window.location.href = "/";
      return;
    }

    const file = fileRef.current?.files?.[0];
    if (!file) {
      setStatus("Pick a CSV file first.");
      return;
    }

    setBusy(true);
    setStatus("Uploading...");

    try {
      const form = new FormData();
      form.append("file", file);

      const res = await fetch(apiBase.replace(/\/$/, "") + "/leads/import", {
        method: "POST",
        headers: {
          Authorization: "Bearer " + token,
        },
        body: form,
      });

      const data = await res.json().catch(() => ({}));
      if (responseRef.current) {
        responseRef.current.textContent = JSON.stringify(data, null, 2);
      }
      setStatus(res.ok ? "Done." : `Failed (${res.status}).`);
    } catch (err: any) {
      setStatus("Error: " + (err?.message || err));
      if (responseRef.current) responseRef.current.textContent = "";
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-10">
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-copper-500/20 ring-1 ring-copper-500/40">
            <Image src="/copper.png" alt="Copper" width={56} height={56} />
          </div>
          <div>
            <div className="text-lg font-semibold leading-tight">CSV Import</div>
            <p className="text-sm text-slate-400">Uploads to /leads/import</p>
          </div>
        </div>
        <button
          onClick={() => {
            storage.clearToken();
            window.location.href = "/";
          }}
          className="rounded-full border border-white/10 px-4 py-2 text-sm text-slate-200 hover:border-copper-400 hover:text-white"
        >
          Sign out
        </button>
      </header>

      <section className="glass rounded-2xl p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <label className="space-y-2 block">
              <div className="text-sm font-medium text-slate-200">CSV file</div>
              <input
                ref={fileRef}
                type="file"
                accept=".csv,text/csv"
                className="w-full rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-copper-400 focus:outline-none"
              />
              <p className="text-xs text-slate-500">
                Required headers: Company, Work Email or Personal Email, First Name.
              </p>
            </label>

            <button
              disabled={!tokenOk || busy}
              onClick={handleUpload}
              className="btn rounded-lg bg-copper-500 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-copper-400 disabled:bg-slate-700 disabled:text-slate-300"
            >
              {busy ? "Uploading..." : "Upload"}
            </button>
            <p className="text-sm text-slate-300">{status}</p>
          </div>

          <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-white/10 bg-black/20 p-4">
            <Image src="/copper.png" alt="Copper mascot" width={160} height={160} className="hero-img" />
            <p className="text-center text-sm text-slate-400">
              Your token is stored locally. We won&apos;t show it here.
            </p>
          </div>
        </div>
      </section>

      <section className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Response</h2>
          <button
            onClick={async () => {
              const txt = responseRef.current?.textContent || "";
              try {
                await navigator.clipboard.writeText(txt);
                setStatus("Response copied.");
              } catch {
                setStatus("Copy failed.");
              }
            }}
            className="btn rounded-lg border border-white/10 px-3 py-1 text-xs text-slate-200 hover:border-copper-400"
          >
            Copy
          </button>
        </div>
        <pre
          ref={responseRef}
          className="mt-3 max-h-96 overflow-auto rounded-lg bg-slate-950 p-4 text-sm text-copper-100"
        ></pre>
      </section>
    </main>
  );
}
