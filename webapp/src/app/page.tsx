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
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(226,95,26,0.15),transparent_30%),radial-gradient(circle_at_80%_0%,rgba(111,152,255,0.08),transparent_30%)]" />
      <div className="relative mx-auto flex min-h-screen max-w-6xl items-center justify-center px-6 py-16">
        <div className="grid w-full gap-10 rounded-3xl border border-white/10 bg-slate-900/75 p-10 shadow-2xl lg:grid-cols-2">
          <div className="flex flex-col justify-center gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-copper-500/20 ring-1 ring-copper-500/40">
                <Image
                  src="/copper.png"
                  alt="Copper"
                  width={56}
                  height={56}
                  className="hero-img"
                />
              </div>
              <div>
                <div className="text-2xl font-semibold">Copper CRM</div>
                <p className="text-sm text-slate-400">Just sign in with Google.</p>
              </div>
            </div>
            <h1 className="text-4xl font-semibold leading-tight">Welcome back</h1>
            <p className="text-sm text-slate-400">
              Tap the Google button below. We’ll take you straight to CSV imports—no extra setup shown.
            </p>
            <div id="gsi-btn" className="mt-4" />
            <p className="text-xs text-slate-400">{status}</p>
            {!ready && (
              <div className="h-1 w-24 rounded bg-white/10">
                <div className="h-1 w-12 animate-pulse rounded bg-copper-500" />
              </div>
            )}
          </div>
          <div className="relative flex items-center justify-center">
            <div className="absolute h-80 w-80 rounded-full bg-copper-500/15 blur-3xl" />
            <div className="relative flex flex-col items-center gap-4 rounded-3xl bg-white/5 p-6 shadow-xl ring-1 ring-white/10">
              <Image
                src="/copper.png"
                alt="Copper mascot"
                width={360}
                height={360}
                className="hero-img"
              />
              <p className="text-center text-sm text-slate-300">
                A single tap gets you in. Then we’ll whisk you to uploads.
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
