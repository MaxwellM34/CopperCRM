"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "../../../components/AppShell";
import { storage } from "../../../lib/storage";

type CompanyLead = {
  id: number;
  first_name?: string | null;
  last_name?: string | null;
  work_email?: string | null;
  email?: string | null;
  job_title?: string | null;
  seniority?: string | null;
  departments?: string | null;
};

type CompanyDetail = {
  id: number;
  company_name: string;
  industry?: string | null;
  country?: string | null;
  company_city?: string | null;
  company_email?: string | null;
  company_phone?: string | null;
  employees_amount?: string | null;
  technologies?: string | null;
  latest_funding?: string | null;
  latest_funding_date?: string | null;
  annual_revenue?: string | null;
  company_address?: string | null;
  facebook?: string | null;
  twitter?: string | null;
  youtube?: string | null;
  instagram?: string | null;
  website?: string | null;
  linkedin?: string | null;
  leads: CompanyLead[];
};

export default function CompanyProfilePage({ params }: { params: { id: string } }) {
  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCompany = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = storage.getToken();
        const apiBase = storage.getApiBaseUrl().replace(/\/$/, "");
        const res = await fetch(`${apiBase}/companies/${params.id}`, {
          headers: token ? { Authorization: "Bearer " + token } : undefined,
        });
        if (res.status === 401) {
          setError("Unauthorized. Please sign in.");
          window.location.href = "/";
          return;
        }
        if (!res.ok) throw new Error(`Failed to fetch company (${res.status})`);
        const data = await res.json();
        setCompany(data ?? null);
      } catch (err: any) {
        setError(err.message ?? "Failed to fetch company");
      } finally {
        setLoading(false);
      }
    };
    fetchCompany();
  }, [params.id]);

  return (
    <AppShell title="Company profile" subtitle="Company summary and linked leads.">
      <section className="profile-hero">
        <div className="profile-hero__copy">
          <p className="eyebrow">Company</p>
          <h2>{company?.company_name || "Company"}</h2>
          <p className="muted">Summary and social links from the companies table.</p>
        </div>
      </section>

      {loading && <p className="muted">Loading company...</p>}
      {error && <p className="text-red-400">Error: {error}</p>}

      {!loading && !error && company && (
        <div className="profile-grid">
          <section className="profile-card glass">
            <h3>Company summary</h3>
            <div className="profile-list">
              <div>
                <span className="muted">Industry</span>
                <strong>{company.industry || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">City</span>
                <strong>{company.company_city || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Country</span>
                <strong>{company.country || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Address</span>
                <strong>{company.company_address || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Employees</span>
                <strong>{company.employees_amount || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Revenue</span>
                <strong>{company.annual_revenue || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Funding</span>
                <strong>{company.latest_funding || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Funding date</span>
                <strong>
                  {company.latest_funding_date ? new Date(company.latest_funding_date).toLocaleDateString() : "n/a"}
                </strong>
              </div>
            </div>
          </section>

          <section className="profile-card glass">
            <h3>Contact + links</h3>
            <div className="profile-list">
              <div>
                <span className="muted">Email</span>
                <strong>{company.company_email || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Phone</span>
                <strong>{company.company_phone || "n/a"}</strong>
              </div>
              <div>
                <span className="muted">Tech stack</span>
                <strong>{company.technologies || "n/a"}</strong>
              </div>
            </div>
            {(company.website || company.linkedin) && (
              <>
                <div className="profile-divider" />
                <div className="profile-links">
                  {company.website && (
                    <a href={company.website} target="_blank" rel="noreferrer">
                      Website
                    </a>
                  )}
                  {company.linkedin && (
                    <a href={company.linkedin} target="_blank" rel="noreferrer">
                      LinkedIn
                    </a>
                  )}
                </div>
              </>
            )}
          </section>

          <section className="profile-card glass">
            <h3>Leads at this company</h3>
            {company.leads.length === 0 && <p className="muted">No leads linked yet.</p>}
            {company.leads.length > 0 && (
              <div className="company-leads">
                {company.leads.map((lead) => {
                  const name = `${lead.first_name ?? ""} ${lead.last_name ?? ""}`.trim() || "Unnamed lead";
                  return (
                    <div key={lead.id} className="company-lead">
                      <div>
                        <Link href={`/leads/${lead.id}`} className="lead-link">
                          {name}
                        </Link>
                      </div>
                      <div className="muted text-xs">{lead.work_email || lead.email || "n/a"}</div>
                      <div className="muted text-xs">{lead.seniority || "Stage pending"}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}
