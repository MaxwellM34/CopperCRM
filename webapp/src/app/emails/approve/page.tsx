"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import AppShell from "../../../components/AppShell";
import { storage } from "../../../lib/storage";

type PendingEmail = {
  id: number;
  first_email: string;
  lead_name?: string | null;
  lead_email?: string | null;
  lead_title?: string | null;
  company_name?: string | null;
  human_approval?: boolean | null;
};

type ApiState = "idle" | "loading" | "done";

export default function ApproveEmailsPage() {
  const apiBase = useMemo(
    () =>
      (process.env.NEXT_PUBLIC_API_BASE || storage.getApiBaseUrl() || "http://127.0.0.1:8000").replace(
        /\/$/,
        "",
      ),
    [],
  );

  const [email, setEmail] = useState<PendingEmail | null>(null);
  const [status, setStatus] = useState<ApiState>("idle");
  const [message, setMessage] = useState("Loading next email...");
  const [flash, setFlash] = useState<"approve" | "reject" | null>(null);
  const [pendingCount, setPendingCount] = useState<number | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const startX = useRef<number | null>(null);
  const dragging = useRef(false);

  const fetchNext = async () => {
    setStatus("loading");
    setFlash(null);
    try {
      const res = await fetch(`${apiBase}/first-emails/next`);
      const data = await res.json();
      if (data?.status === "no_pending") {
        setEmail(null);
        setMessage("No pending emails to review.");
      } else {
        setEmail(data);
        setMessage("");
      }
    } catch (e: any) {
      setMessage(`Failed to fetch from ${apiBase}: ${e?.message || e}`);
    } finally {
      setStatus("done");
    }
    // also refresh pending count
    try {
      const res = await fetch(`${apiBase}/first-emails/stats`);
      const data = await res.json();
      setPendingCount(data?.pending ?? null);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    fetchNext();
  }, []);

  const sendDecision = async (decision: "approved" | "rejected") => {
    if (!email) return;
    setFlash(decision === "approved" ? "approve" : "reject");
    try {
      await fetch(`${apiBase}/first-emails/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: email.id, decision }),
      });
    } catch (e: any) {
      setMessage(`Failed to send decision: ${e?.message || e}`);
    } finally {
      setTimeout(fetchNext, 120);
    }
  };

  const onSwipeStart = (x: number) => {
    dragging.current = true;
    startX.current = x;
    if (cardRef.current) cardRef.current.style.transition = "transform 0s linear";
  };

  const onSwipeMove = (x: number) => {
    if (!dragging.current || startX.current === null || !cardRef.current) return;
    const dx = x - startX.current;
    cardRef.current.style.transform = `translateX(${dx * 0.3}px) rotate(${dx * 0.05}deg)`;
  };

  const onSwipeEnd = (x: number) => {
    if (!dragging.current || startX.current === null || !cardRef.current) return;
    const dx = x - startX.current;
    dragging.current = false;
    startX.current = null;
    const threshold = 80;

    if (Math.abs(dx) > threshold) {
      if (dx > 0) {
        sendDecision("approved");
      } else {
        sendDecision("rejected");
      }
    }
    if (cardRef.current) {
      cardRef.current.style.transition = "transform 0.15s ease-out";
      cardRef.current.style.transform = "translateX(0px) rotate(0deg)";
      setTimeout(() => {
        if (cardRef.current) cardRef.current.style.transition = "transform 0s linear";
      }, 160);
    }
  };

  const name = email?.lead_name || "Lead";
  const subtitleParts = [
    email?.lead_title,
    email?.company_name ? `at ${email.company_name}` : null,
    email?.lead_email,
  ].filter(Boolean);

  return (
    <AppShell title="Approve Emails" subtitle="Swipe right to approve, left to reject.">
      <section className="glass rounded-2xl p-6 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <p className="eyebrow">Pending</p>
            <h2 className="text-2xl font-semibold">{pendingCount ?? "…"}</h2>
            <p className="muted text-sm">Emails waiting for human approval.</p>
          </div>
          <button className="btn subtle text-sm" onClick={fetchNext} disabled={status === "loading"}>
            Refresh
          </button>
        </div>
      </section>

      <section className="glass rounded-2xl p-6">
        {email ? (
          <div
            ref={cardRef}
            className="rounded-2xl border border-white/10 bg-black/30 p-5 relative select-none"
            onMouseDown={(e) => onSwipeStart(e.clientX)}
            onMouseMove={(e) => onSwipeMove(e.clientX)}
            onMouseUp={(e) => onSwipeEnd(e.clientX)}
            onMouseLeave={(e) => onSwipeEnd(e.clientX)}
            onTouchStart={(e) => onSwipeStart(e.touches[0].clientX)}
            onTouchMove={(e) => onSwipeMove(e.touches[0].clientX)}
            onTouchEnd={(e) => onSwipeEnd(e.changedTouches[0].clientX)}
          >
            <p className="eyebrow">Email to {name}</p>
            <h3 className="text-xl font-semibold">{subtitleParts.join(" • ")}</h3>
            <div className="mt-4 rounded-xl border border-white/5 bg-slate-950/60 p-4 text-base leading-relaxed whitespace-pre-wrap">
              {email.first_email || "(no email body)"}
            </div>

            <div className="mt-5 flex gap-3">
              <button className="btn btn-reject" onClick={() => sendDecision("rejected")}>
                Reject
              </button>
              <button className="btn btn-approve" onClick={() => sendDecision("approved")}>
                Approve
              </button>
            </div>
          </div>
        ) : (
          <p className="muted text-sm">{message || "No pending emails."}</p>
        )}
      </section>

      {flash && (
        <div className={`decision-flash ${flash === "approve" ? "decision-flash-approve" : "decision-flash-reject"}`}>
          <div className="decision-flash-inner">{flash === "approve" ? "APPROVED" : "REJECTED"}</div>
        </div>
      )}
    </AppShell>
  );
}
