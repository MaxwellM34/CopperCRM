"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";
import { storage } from "../../../lib/storage";
import ReactCountryFlag from "react-country-flag";
import { getCode } from "country-list";

type LeadDetail = {
  id: number;
  email?: string | null;
  work_email?: string | null;
  gender?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
  company_id?: number | null;
  company_name?: string | null;
  job_title?: string | null;
  person_address?: string | null;
  country?: string | null;
  personal_linkedin?: string | null;
  seniority?: string | null;
  departments?: string | null;
  industries?: string | null;
  profile_summary?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export default function LeadProfilePage({ params }: { params: { id: string } }) {
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLead = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = storage.getToken();
        const apiBase = storage.getApiBaseUrl().replace(/\/$/, "");
        const res = await fetch(`${apiBase}/leads/${params.id}`, {
          headers: token ? { Authorization: "Bearer " + token } : undefined,
        });
        if (res.status === 401) {
          setError("Unauthorized. Please sign in.");
          window.location.href = "/";
          return;
        }
        if (!res.ok) throw new Error(`Failed to fetch lead (${res.status})`);
        const data = await res.json();
        setLead(data ?? null);
      } catch (err: any) {
        setError(err.message ?? "Failed to fetch lead");
      } finally {
        setLoading(false);
      }
    };
    fetchLead();
  }, [params.id]);

  const countryCode = useMemo(() => {
    if (!lead?.country) return null;
    const code = getCode(lead.country);
    return code ? code.toUpperCase() : null;
  }, [lead?.country]);

  const gender = (lead?.gender || "unknown_gender").toLowerCase();
  const avatar =
    lead?.avatar_url ||
    (gender === "female" ? "/femaleAvatar.png" : gender === "male" ? "/maleAvatar.png" : "/unspecifiedAvatar.png");

  return (
    <AppShell title="Lead profile" subtitle="Lead details and activity overview.">
      <section className="profile-hero">
        <div className="profile-hero__copy">
          <p className="eyebrow">Lead</p>
          <h2>{lead ? `${lead.first_name ?? ""} ${lead.last_name ?? ""}`.trim() || "Unnamed lead" : ""}</h2>
          <p className="muted">Stage and activity placeholders until tracking is enabled.</p>
        </div>
        <div className="profile-hero__avatar">
          <Image src={avatar} alt="Lead avatar" width={88} height={88} className="lead-avatar" />
        </div>
      </section>

      {loading && <p className="muted">Loading lead...</p>}
      {error && <p className="text-red-400">Error: {error}</p>}

      {!loading && !error && lead && (
        <div className="profile-grid">
          <section className="profile-card glass">
            <div className="profile-card__header">
              <h3>Contact info</h3>
              {lead.personal_linkedin && (
                <a href={lead.personal_linkedin} className="btn ghost text-xs" target="_blank" rel="noreferrer">
                  LinkedIn
                </a>
              )}
            </div>
            <div className="profile-list">
              <div>
                <span className="muted">Primary email</span>
                <strong>{lead.work_email || lead.email || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Job title</span>
                <strong>{lead.job_title || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Seniority</span>
                <strong>{lead.seniority || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Departments</span>
                <strong>{lead.departments || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Industry</span>
                <strong>{lead.industries || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Location</span>
                <strong>{lead.country || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Company</span>
                {lead.company_id && lead.company_name ? (
                  <Link href={`/companies/${lead.company_id}`} className="lead-link">
                    {lead.company_name}
                  </Link>
                ) : (
                  <strong>{lead.company_name || "n/a"}</strong>
                )}
              </div>
            </div>
          </section>

          <section className="profile-card glass">
            <h3>Pipeline stage</h3>
            <p className="muted">Prospect (placeholder)</p>
            <div className="profile-divider" />
            <h3>Recent activity</h3>
            <ul className="profile-activity">
              <li>Last email: not tracked yet</li>
              <li>Last reply: not tracked yet</li>
              <li>Last interaction: not tracked yet</li>
            </ul>
            <div className="profile-divider" />
            <h3>Timeline</h3>
            <div className="profile-list">
              <div>
                <span className="muted">Created</span>
                <strong>{lead.created_at ? new Date(lead.created_at).toLocaleString() : "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Updated</span>
                <strong>{lead.updated_at ? new Date(lead.updated_at).toLocaleString() : "n/a"}</strong>
              </div>
            </div>
          </section>

          <section className="profile-card glass">
            <div className="profile-card__header">
              <h3>Profile summary</h3>
              {countryCode && (
                <div className="flag-wrap">
                  <ReactCountryFlag countryCode={countryCode} svg style={{ width: "1.6em", height: "1.1em" }} />
                  <span className="muted text-xs">{lead.country}</span>
                </div>
              )}
            </div>
            <p className="muted">{lead.profile_summary || "No profile summary yet."}</p>
          </section>
        </div>
      )}
    </AppShell>
  );
}
