"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { loadGsi } from "../lib/google";
import { storage } from "../lib/storage";

const clientId =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ||
  "468831678336-70ia3bv84h9ifgt5d1agqjhn7ao05eg2.apps.googleusercontent.com";

export default function Home() {
  const [status, setStatus] = useState<string>("Sign in with Google to continue.");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    storage.setApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000");
  }, []);

  useEffect(() => {
    async function init() {
      try {
        await loadGsi();
        if (!(window as any).google?.accounts?.id) {
          setStatus("Google not available.");
          return;
        }
        (window as any).google.accounts.id.initialize({
          client_id: clientId,
          callback: (resp: any) => {
            const token = resp?.credential;
            if (token) {
              storage.setToken(token);
              setStatus("Signed in. Redirecting...");
              setTimeout(() => {
                window.location.href = "/import";
              }, 400);
            } else {
              setStatus("No token returned.");
            }
          },
          ux_mode: "popup",
        });
        (window as any).google.accounts.id.renderButton(
          document.getElementById("gsi-btn"),
          { theme: "outline", size: "large", shape: "pill", text: "signin_with" }
        );
        setReady(true);
      } catch (e: any) {
        setStatus(e?.message || "Google init failed");
      }
    }
    init();
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-6 py-12">
      <div className="grid gap-8 rounded-3xl border border-white/10 bg-slate-900/70 p-8 shadow-2xl md:grid-cols-2">
        <div className="flex flex-col justify-center gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-copper-500/20 ring-1 ring-copper-500/40">
              <Image
                src="/copper.png"
                alt="Copper"
                width={40}
                height={40}
                className="hero-img"
              />
            </div>
            <div>
              <div className="text-xl font-semibold">Copper CRM</div>
              <p className="text-sm text-slate-400">Welcome back.</p>
            </div>
          </div>
          <h1 className="text-3xl font-semibold leading-tight">Sign in with Google</h1>
          <p className="text-sm text-slate-400">
            We only need your Google login to proceed to imports. No URLs or tokens shown.
          </p>
          <div id="gsi-btn" className="mt-4" />
          <p className="text-xs text-slate-400">{status}</p>
          {!ready && (
            <div className="h-1 w-24 rounded bg-white/10">
              <div className="h-1 w-12 animate-pulse rounded bg-copper-500" />
            </div>
          )}
        </div>
        <div className="flex flex-col items-center justify-center gap-4">
          <Image
            src="/copper.png"
            alt="Copper mascot"
            width={280}
            height={280}
            className="hero-img"
          />
          <p className="text-center text-sm text-slate-400">
            After signing in, you&apos;ll jump straight to CSV imports.
          </p>
        </div>
      </div>
    </main>
  );
}
