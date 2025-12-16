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

  useEffect(() => {
    // Pick sensible default: local API in dev, Cloud Run in prod (overridable via env/localStorage)
    storage.setApiBaseUrl(storage.getApiBaseUrl());
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
