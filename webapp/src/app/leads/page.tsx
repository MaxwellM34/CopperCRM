"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import AppShell from "../../components/AppShell";
import { storage } from "../../lib/storage";
import ReactCountryFlag from "react-country-flag";
import { getCode } from "country-list";

type LeadRow = {
  email?: string | null;
  work_email?: string | null;
  gender?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  company_name?: string | null;
  job_title?: string | null;
  person_address?: string | null;
  country?: string | null;
  personal_linkedin?: string | null;
  seniority?: string | null;
  departments?: string | null;
};

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLeads = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = storage.getToken();
        const apiBase = storage.getApiBaseUrl().replace(/\/$/, "");
        const res = await fetch(`${apiBase}/leads/display`, {
          headers: { Authorization: "Bearer " + token },
        });
        if (!res.ok) throw new Error(`Failed to fetch leads (${res.status})`);
        const data = await res.json();
        setLeads(data ?? []);
      } catch (err: any) {
        setError(err.message ?? "Failed to fetch leads");
      } finally {
        setLoading(false);
      }
    };
    fetchLeads();
  }, []);

  return (
    <AppShell title="Leads" subtitle="Coming soon: richer lead workspace with filters and bulk actions.">
      <div className="lead-hero">
        <div>
          <p className="pill pill-muted text-xs">Preview</p>
          <h2 className="mt-2">Leads roster</h2>
          <p className="muted">Avatar by gender, flag by country, and a single contact email.</p>
        </div>
      </div>

      <div className="lead-table-card">
        {loading && <p className="muted">Loading leads…</p>}
        {error && <p className="text-red-400">Error: {error}</p>}
        {!loading && !error && (
          <div className="lead-table">
            <div className="lead-row lead-header">
              <span>Lead</span>
              <span>Contact email</span>
              <span>Job title</span>
              <span>Department</span>
              <span>Seniority</span>
              <span>Country</span>
              <span>LinkedIn</span>
            </div>
            {leads.map((lead, idx) => (
              <LeadRowItem key={`${lead.email}-${idx}`} lead={lead} />
            ))}
            {leads.length === 0 && <p className="muted mt-2">No leads yet.</p>}
          </div>
        )}
      </div>
    </AppShell>
  );
}

function LeadRowItem({ lead }: { lead: LeadRow }) {
  const contactEmail = lead.work_email || lead.email || "";
  const gender = (lead.gender || "unknown_gender").toLowerCase();
  const avatar =
    gender === "female" ? "/femaleAvatar.png" : gender === "male" ? "/maleAvatar.png" : "/unspecifiedAvatar.png";

  const countryCode = useMemo(() => {
    const code = lead.country ? getCode(lead.country) : null;
    return code ? code.toUpperCase() : null;
  }, [lead.country]);

  return (
    <div className="lead-row">
      <div className="lead-cell lead-person">
        <Image src={avatar} alt="avatar" width={42} height={42} className="lead-avatar" />
        <div>
          <div className="font-semibold">
            {lead.first_name || lead.last_name ? `${lead.first_name ?? ""} ${lead.last_name ?? ""}`.trim() : "—"}
          </div>
          <div className="muted text-xs">{lead.company_name || "Company pending"}</div>
        </div>
      </div>
      <div className="lead-cell">{contactEmail || "—"}</div>
      <div className="lead-cell">{lead.job_title || "—"}</div>
      <div className="lead-cell">{lead.departments || "—"}</div>
      <div className="lead-cell">{lead.seniority || "—"}</div>
      <div className="lead-cell lead-flag">
        {countryCode ? (
          <div className="flag-wrap">
            <ReactCountryFlag countryCode={countryCode} svg style={{ width: "1.8em", height: "1.2em" }} />
            <span className="muted text-xs">{lead.country}</span>
          </div>
        ) : (
          <span className="muted">—</span>
        )}
      </div>
      <div className="lead-cell">
        {lead.personal_linkedin ? (
          <a href={lead.personal_linkedin} className="text-emerald-300 hover:underline" target="_blank" rel="noreferrer">
            Profile
          </a>
        ) : (
          <span className="muted">—</span>
        )}
      </div>
    </div>
  );
}
