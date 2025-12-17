"use client";

import AppShell from "../../components/AppShell";

const bars = [
  { label: "Opens", value: 48, fill: "from-emerald-500 via-green-400 to-lime-300" },
  { label: "Replies", value: 9, fill: "from-sky-500 via-cyan-400 to-emerald-300" },
  { label: "Bounces", value: 1.2, fill: "from-rose-500 via-pink-500 to-orange-400" },
  { label: "Clicks", value: 14, fill: "from-amber-500 via-yellow-400 to-lime-300" },
];

const areaPoints = [34, 39, 46, 51, 47, 44, 49, 55, 58, 61, 59, 63];
const donut = [
  { label: "Delivered", value: 82, color: "#10b981" },
  { label: "Soft bounce", value: 5, color: "#f59e0b" },
  { label: "Hard bounce", value: 3, color: "#ef4444" },
  { label: "Deferred", value: 10, color: "#6b7280" },
];

const conversionSteps = [
  { label: "Sent", value: "12,400" },
  { label: "Opened", value: "5,920" },
  { label: "Clicked", value: "1,820" },
  { label: "Replied", value: "1,040" },
  { label: "Qualified", value: "280" },
  { label: "Won", value: "18" },
];

const sequenceHealth = [
  { label: "Sequence A (SDR)", value: "52.3% open · 9.1% reply", delta: "+1.2 pts" },
  { label: "Sequence B (AE)", value: "48.7% open · 7.6% reply", delta: "+0.4 pts" },
  { label: "Sequence C (Nurture)", value: "35.2% open · 4.2% reply", delta: "-0.6 pts" },
];

export default function ReportsPage() {
  return (
    <AppShell title="Reports" subtitle="Sample dashboard with placeholder charts and CRM metrics.">
      <div className="reports-grid">
        <div className="report-card">
          <PanelHeader title="Outbound snapshot" pill="Last 7d" />
          <div className="bar-grid">
            {bars.map((b) => (
              <div key={b.label} className="bar-card">
                <p className="muted text-xs uppercase tracking-wide">{b.label}</p>
                <div className="bar-shell">
                  <div
                    className="bar-fill"
                    style={{ height: `${Math.max(12, b.value)}%`, background: b.fill }}
                  />
                </div>
                <p className="text-lg font-semibold">{b.value}%</p>
              </div>
            ))}
          </div>
        </div>

        <div className="report-card">
          <PanelHeader title="Opens trend" pill="Area chart" />
          <div className="chart-shell">
            <AreaChart points={areaPoints} />
          </div>
        </div>

        <div className="report-card">
          <PanelHeader title="Deliverability" pill="Sample" />
          <div className="donut-shell">
            <Donut data={donut} />
          </div>
          <div className="legend">
            {donut.map((d) => (
              <div key={d.label} className="legend-row">
                <span className="legend-dot" style={{ backgroundColor: d.color }} />
                <span className="muted">{d.label}</span>
                <span className="legend-val">{d.value}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="report-card">
          <PanelHeader title="Funnel" pill="Placeholder" />
          <div className="funnel">
            {conversionSteps.map((step, idx) => (
              <div key={step.label} className="funnel-row">
                <div className="funnel-label">{step.label}</div>
                <div className="funnel-bar">
                  <div
                    className="funnel-bar-fill"
                    style={{ width: `${Math.max(8, 90 - idx * 12)}%` }}
                  />
                </div>
                <div className="funnel-val">{step.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function PanelHeader({ title, pill }: { title: string; pill?: string }) {
  return (
    <div className="flex items-center justify-between">
      <p className="eyebrow">{title}</p>
      {pill && <span className="pill pill-muted text-xs">{pill}</span>}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="muted">{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}

function AreaChart({ points }: { points: number[] }) {
  const max = Math.max(...points);
  const min = Math.min(...points);
  const span = max - min || 1;
  return (
    <div className="w-full h-40 bg-gradient-to-b from-slate-900 via-slate-950 to-black rounded-xl border border-white/5 relative overflow-hidden">
      <svg width="100%" height="100%" preserveAspectRatio="none" viewBox="0 0 100 100">
        <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fb923c" stopOpacity="0.75" />
          <stop offset="100%" stopColor="#0f172a" stopOpacity="0" />
        </linearGradient>
        <path
          d={buildPath(points.map((p, i) => [i * (100 / (points.length - 1)), 100 - ((p - min) / span) * 90 - 5]))}
          fill="url(#areaGradient)"
          stroke="#fb923c"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function buildPath(points: [number, number][]): string {
  if (!points.length) return "";
  const d = [`M ${points[0][0]} ${points[0][1]}`];
  for (let i = 1; i < points.length; i++) {
    d.push(`L ${points[i][0]} ${points[i][1]}`);
  }
  d.push(`L 100 100 L 0 100 Z`);
  return d.join(" ");
}

function Donut({ data }: { data: { label: string; value: number; color: string }[] }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  let offset = 0;
  const radius = 42;
  return (
    <svg viewBox="0 0 120 120" className="mx-auto h-32 w-32">
      {data.map((d, idx) => {
        const dash = (d.value / total) * 2 * Math.PI * radius;
        const circle = (
          <circle
            key={idx}
            r={radius}
            cx="60"
            cy="60"
            fill="transparent"
            stroke={d.color}
            strokeWidth="14"
            strokeDasharray={`${dash} ${2 * Math.PI * radius}`}
            strokeDashoffset={offset}
            transform="rotate(-90 60 60)"
          />
        );
        offset -= dash;
        return circle;
      })}
      <circle r={28} cx="60" cy="60" fill="rgba(15,23,42,0.8)" />
      <text x="60" y="58" textAnchor="middle" fill="#e2e8f0" fontSize="12" fontWeight="700">
        Deliverability
      </text>
    </svg>
  );
}
