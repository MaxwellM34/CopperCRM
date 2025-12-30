"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { loadGsi } from "../lib/google";
import { storage } from "../lib/storage";

const clientId =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ||
  "468831678336-70ia3bv84h9ifgt5d1agqjhn7ao05eg2.apps.googleusercontent.com";

export default function Home() {
  const [status, setStatus] = useState<string>("Sign in with Google to continue.");
  const [buttonReady, setButtonReady] = useState(false);
  const buttonHostRef = useRef<HTMLDivElement>(null);
  const renderedRef = useRef(false);
  const [bills, setBills] = useState<
    {
      id: number;
      left: number;
      duration: number;
      delay: number;
      size: number;
      opacity: number;
      tilt: number;
      sway: number;
      spin: number;
    }[]
  >([]);

  useEffect(() => {
    // Pick sensible default: local API in dev, Cloud Run in prod (overridable via env/localStorage)
    storage.setApiBaseUrl(storage.getApiBaseUrl());
  }, []);

  useEffect(() => {
    // If auth is disabled on the API, skip the Google flow entirely.
    (async () => {
      try {
        const apiBase = storage.getApiBaseUrl().replace(/\/$/, "");
        const token = storage.getToken();
        const headers = token ? { Authorization: "Bearer " + token } : {};
        const res = await fetch(`${apiBase}/auth/me`, { headers });
        if (res.ok) {
          setStatus("Auth bypass enabled. Redirecting...");
          setTimeout(() => {
            window.location.href = "/crm";
          }, 250);
        }
      } catch {
        // ignore and fall back to Google login
      }
    })();
  }, []);

  useEffect(() => {
    // Generate a handful of floating bills with varied timing/size
    const items = Array.from({ length: 28 }).map((_, i) => ({
      id: i,
      left: Math.random() * 100, // percent across screen
      duration: 10 + Math.random() * 8, // seconds
      delay: Math.random() * 8,
      size: 140 + Math.random() * 140,
      opacity: 0.35 + Math.random() * 0.35,
      tilt: -15 + Math.random() * 30,
      sway: 18 + Math.random() * 36,
      spin: 160 + Math.random() * 320,
    }));
    setBills(items);
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
                window.location.href = "/crm";
              }, 400);
            } else {
              setStatus("No token returned.");
            }
          },
          ux_mode: "popup",
        });
        if (buttonHostRef.current && !renderedRef.current) {
          (window as any).google.accounts.id.renderButton(buttonHostRef.current, {
            theme: "outline",
            size: "large",
            shape: "rectangular",
            text: "continue_with",
          });
          renderedRef.current = true;
          setButtonReady(true);
        }
      } catch (e: any) {
        setStatus(e?.message || "Google init failed");
      }
    }
    init();
  }, []);

  return (
    <main className="login-screen">
      <div className="money-field">
        {bills.map((bill) => (
          <div
            key={bill.id}
            className="bill"
            style={
              {
                "--left": `${bill.left}%`,
                "--bill-size": `${bill.size}px`,
                "--bill-opacity": bill.opacity,
                "--bill-tilt": `${bill.tilt}deg`,
                "--bill-duration": `${bill.duration}s`,
                "--bill-delay": `${bill.delay}s`,
                "--bill-sway": `${bill.sway}px`,
                "--bill-spin": `${bill.spin}deg`,
              } as React.CSSProperties
            }
          >
            <div className="bill-glow" />
            <span className="bill-mark">$100</span>
          </div>
        ))}
      </div>
      <div className="login-backdrop" />
      <div className="login-card glass">
        <Image src="/copper.png" alt="Copper" width={240} height={240} className="login-logo" />
        <h1 className="login-title">Copper</h1>
        <div className="login-box">
          {!buttonReady && (
            <button className="fallback-google-btn" onClick={() => setStatus("Loading Google...")}>
              Google Login
            </button>
          )}
          <div ref={buttonHostRef} className="gsi-btn-slot" />
        </div>
        <p className="login-status">{status}</p>
      </div>
    </main>
  );
}
