"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "../../components/AppShell";
import { storage } from "../../lib/storage";
import ReactCountryFlag from "react-country-flag";
import { getCode } from "country-list";

type CompanySummary = {
  id: number;
  company_name: string;
  industry?: string | null;
  employees_amount?: string | null;
  country?: string | null;
};

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCompanies = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = storage.getToken();
        const apiBase = storage.getApiBaseUrl().replace(/\/$/, "");
        const res = await fetch(`${apiBase}/companies`, {
          headers: token ? { Authorization: "Bearer " + token } : undefined,
        });
        if (res.status === 401) {
          setError("Unauthorized. Please sign in.");
          window.location.href = "/";
          return;
        }
        if (!res.ok) throw new Error(`Failed to fetch companies (${res.status})`);
        const data = await res.json();
        setCompanies(data ?? []);
      } catch (err: any) {
        setError(err.message ?? "Failed to fetch companies");
      } finally {
        setLoading(false);
      }
    };
    fetchCompanies();
  }, []);

  return (
    <AppShell title="Companies" subtitle="Company profiles with linked leads.">
      <div className="lead-hero">
        <div>
          <p className="pill pill-muted text-xs">Directory</p>
          <h2 className="mt-2">Companies list</h2>
          <p className="muted">Company name, industry, size, and country.</p>
        </div>
      </div>

      <div className="company-table-card">
        {loading && <p className="muted">Loading companies...</p>}
        {error && <p className="text-red-400">Error: {error}</p>}
        {!loading && !error && (
          <div className="company-table">
            <div className="company-row company-header">
              <span>Company</span>
              <span>Industry</span>
              <span>Size</span>
              <span>Country</span>
            </div>
            {companies.map((company) => (
              <CompanyRow key={company.id} company={company} />
            ))}
            {companies.length === 0 && <p className="muted mt-2">No companies yet.</p>}
          </div>
        )}
      </div>
    </AppShell>
  );
}

function CompanyRow({ company }: { company: CompanySummary }) {
  const countryCode = useMemo(() => {
    if (!company.country) return null;
    const code = getCode(company.country);
    return code ? code.toUpperCase() : null;
  }, [company.country]);

  return (
    <div className="company-row">
      <div className="company-cell">
        <Link href={`/companies/${company.id}`} className="lead-link">
          {company.company_name}
        </Link>
      </div>
      <div className="company-cell">{company.industry || "n/a"}</div>
      <div className="company-cell">{company.employees_amount || "n/a"}</div>
      <div className="company-cell company-flag">
        {countryCode ? (
          <div className="flag-wrap">
            <ReactCountryFlag countryCode={countryCode} svg style={{ width: "1.8em", height: "1.2em" }} />
            <span className="muted text-xs">{company.country}</span>
          </div>
        ) : (
          <span className="muted">n/a</span>
        )}
      </div>
    </div>
  );
}
