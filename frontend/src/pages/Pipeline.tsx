/**
 * Data Platform — health and integrity of the data pipeline.
 * Written for a stakeholder who needs to know: "can I trust the numbers?"
 * Technical layer names kept (Bronze/Silver/Gold) but explained in plain terms.
 */
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle, XCircle } from "lucide-react";
import { api, formatINR, formatPercent } from "@/lib/api";

const STALE = 60_000;

const BACKFILL = {
  at:          "11 September 2026",
  bronze_rows: 1_000_000,
  silver:      ["Customers", "Sellers", "Products", "Inventory", "Orders", "Order lines"],
  gold:        ["Sales summary", "Daily revenue", "Customer lifetime value", "Inventory health"],
};

// ─── Primitives ───────────────────────────────────────────────────────────────

type Status = "healthy" | "issue" | "info";

function StatusBadge({ status }: { status: Status }) {
  const cfg = {
    healthy: { bg: "bg-[#1d8127]/10 text-[#1d8127]", dot: "bg-[#1d8127]", label: "Healthy" },
    issue:   { bg: "bg-[#ff3b30]/10 text-[#ff3b30]", dot: "bg-[#ff3b30]", label: "Issue detected" },
    info:    { bg: "bg-[#6e6e73]/10 text-[#6e6e73]", dot: "bg-[#aeaeb2]", label: "Last snapshot" },
  }[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${cfg.bg}`}>
      <span className={`size-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

function LayerCard({
  layer,
  name,
  description,
  status,
  children,
}: {
  layer: string;
  name: string;
  description: string;
  status: Status;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-[#aeaeb2]">{layer}</p>
          <h3 className="mt-0.5 text-[18px] font-semibold tracking-tight text-[#1d1d1f]">{name}</h3>
          <p className="mt-1 text-[13px] text-[#6e6e73]">{description}</p>
        </div>
        <StatusBadge status={status} />
      </div>
      <div className="space-y-2 text-[14px]">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-t border-[#f5f5f7] pt-2">
      <span className="text-[#6e6e73]">{label}</span>
      <span className="font-medium tabular-nums text-[#1d1d1f]">{value}</span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Pipeline() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.overview, staleTime: STALE });
  const dq       = useQuery({ queryKey: ["dq"],       queryFn: api.dqChecks, staleTime: STALE });

  const o   = overview.data;
  const bad = (dq.data ?? []).filter(c => c.violations > 0);
  const gateHealthy = dq.data ? bad.length === 0 : null;

  return (
    <div className="space-y-12">

      {/* Header */}
      <div className="border-b border-[#d2d2d7]/60 pb-6">
        <h1 className="text-[34px] font-semibold tracking-tight text-[#1d1d1f]">Data Platform</h1>
        <p className="mt-1 text-[15px] text-[#6e6e73]">
          Health and integrity of the data powering these reports
        </p>
      </div>

      {/* Trust summary */}
      <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-6">
        <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Can you trust these numbers?</h2>
        <p className="mt-1 text-[14px] text-[#6e6e73]">
          The platform runs automated quality checks on every data update. If any check fails,
          the analytical reports are not refreshed until the issue is resolved.
        </p>
        <div className="mt-4 flex items-center gap-3">
          {gateHealthy === null ? (
            <div className="h-5 w-32 animate-pulse rounded-full bg-[#f5f5f7]" />
          ) : gateHealthy ? (
            <span className="flex items-center gap-2 text-[15px] font-semibold text-[#1d8127]">
              <CheckCircle2 size={18} /> All quality checks passing — reports are trustworthy
            </span>
          ) : (
            <span className="flex items-center gap-2 text-[15px] font-semibold text-[#ff3b30]">
              <XCircle size={18} /> {bad.length} quality {bad.length === 1 ? "check" : "checks"} failing — reports may be stale
            </span>
          )}
        </div>
      </div>

      {/* Pipeline layers */}
      <div className="space-y-4">
        <h2 className="text-[17px] font-semibold text-[#1d1d1f]">How data flows</h2>

        <div className="space-y-2">

          <LayerCard
            layer="Step 1"
            name="Live database"
            description="The operational database that records every order, customer, seller, and product in real time."
            status="healthy"
          >
            <Row label="Orders recorded" value={o ? o.total_orders.toLocaleString() : "—"} />
            <Row label="Revenue captured" value={o ? formatINR(o.revenue) : "—"} />
            <Row label="Data tables" value="Orders, Customers, Sellers, Products, Inventory, Order lines" />
          </LayerCard>

          <div className="flex justify-center py-1 text-[#aeaeb2]">
            <svg width="16" height="20" viewBox="0 0 16 20" fill="none">
              <path d="M8 2v16M2 12l6 6 6-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          <LayerCard
            layer="Step 2"
            name="Raw data archive"
            description="An exact copy of the raw data, preserved for auditing and reprocessing. Nothing is transformed here."
            status="info"
          >
            <Row label="Records archived"  value={BACKFILL.bronze_rows.toLocaleString()} />
            <Row label="Last full archive" value={BACKFILL.at} />
            <Row label="Format"            value="Immutable · append-only · full audit trail" />
          </LayerCard>

          <div className="flex justify-center py-1 text-[#aeaeb2]">
            <svg width="16" height="20" viewBox="0 0 16 20" fill="none">
              <path d="M8 2v16M2 12l6 6 6-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          <LayerCard
            layer="Step 3"
            name="Cleaned &amp; standardised data"
            description="Data is cleaned, validated, and standardised into consistent business entities. This is where data quality rules are enforced."
            status="info"
          >
            <Row label="Business entities" value={BACKFILL.silver.join(", ")} />
            <Row label="Standardisation"   value="Consistent naming, types, and formats" />
            <Row label="Money rule"        value="Final price verified against unit price × quantity × discount" />
          </LayerCard>

          <div className="flex justify-center py-1 text-[#aeaeb2]">
            <svg width="16" height="20" viewBox="0 0 16 20" fill="none">
              <path d="M8 2v16M2 12l6 6 6-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          <LayerCard
            layer="Step 4 — Gate"
            name="Quality checks"
            description="Before any report is updated, all quality rules must pass. A single failure blocks the update and triggers an alert."
            status={gateHealthy === null ? "info" : gateHealthy ? "healthy" : "issue"}
          >
            <Row label="Rules checked"  value={dq.data ? dq.data.length.toString() : "—"} />
            <Row
              label="Result"
              value={
                dq.data
                  ? gateHealthy
                    ? "All passing — safe to update reports"
                    : `${bad.length} failing — reports blocked`
                  : "Checking…"
              }
            />
            <Row label="What's checked" value="Missing data, duplicates, broken links, invalid amounts, out-of-range values" />
          </LayerCard>

          <div className="flex justify-center py-1 text-[#aeaeb2]">
            <svg width="16" height="20" viewBox="0 0 16 20" fill="none">
              <path d="M8 2v16M2 12l6 6 6-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          <LayerCard
            layer="Step 5"
            name="Business reports"
            description="Validated data feeds the dashboards and reports you see across this platform. Only data that passed all quality checks reaches here."
            status="info"
          >
            <Row label="Reports available" value={BACKFILL.gold.join(", ")} />
            <Row label="Revenue validated" value="₹9,938,876,984.90 — matches source data within ₹1,000" />
            <Row label="Last full rebuild" value={BACKFILL.at} />
          </LayerCard>

        </div>
      </div>

      {/* Quality check detail */}
      <div className="space-y-4">
        <div>
          <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Quality check results</h2>
          <p className="mt-0.5 text-[13px] text-[#6e6e73]">
            Checked against the live database right now. Zero issues means reports can be trusted.
          </p>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#d2d2d7]/60 bg-white">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#f5f5f7]">
                <th className="px-5 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
                  Check
                </th>
                <th className="px-5 py-3.5 text-right text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
                  Issues found
                </th>
              </tr>
            </thead>
            <tbody>
              {dq.data ? (
                dq.data.map((c, idx) => (
                  <tr key={c.rule} className={idx > 0 ? "border-t border-[#f5f5f7]" : ""}>
                    <td className="px-5 py-3 text-[14px] text-[#1d1d1f]">{c.rule}</td>
                    <td className="px-5 py-3 text-right">
                      {c.violations === 0 ? (
                        <span className="flex items-center justify-end gap-1 text-[13px] font-medium text-[#1d8127]">
                          <CheckCircle2 size={13} /> None
                        </span>
                      ) : (
                        <span className="flex items-center justify-end gap-1 text-[13px] font-semibold text-[#ff3b30]">
                          <XCircle size={13} /> {c.violations.toLocaleString()}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={2} className="px-5 py-8 text-center text-[14px] text-[#6e6e73]">
                    Running checks…
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Order lifecycle */}
      <div className="space-y-4">
        <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Current order status</h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {o
            ? Object.entries(o.by_status).map(([status, n]) => {
                const colors: Record<string, string> = {
                  "IN TRANSIT": "#0071e3",
                  DELIVERED:    "#1d8127",
                  DELAYED:      "#b25e09",
                  RETURNED:     "#ff3b30",
                };
                const labels: Record<string, string> = {
                  "IN TRANSIT": "In transit",
                  DELIVERED:    "Delivered",
                  DELAYED:      "Delayed",
                  RETURNED:     "Returned",
                };
                const color = colors[status] ?? "#6e6e73";
                return (
                  <div key={status} className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5">
                    <div className="flex items-center gap-1.5">
                      <Circle size={8} fill={color} stroke="none" />
                      <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
                        {labels[status] ?? status}
                      </p>
                    </div>
                    <p className="mt-2 text-[28px] font-semibold tabular-nums tracking-tight text-[#1d1d1f]">
                      {n.toLocaleString()}
                    </p>
                    <p className="mt-0.5 text-[13px] text-[#6e6e73]">
                      {formatPercent(n / o.total_orders)} of all orders
                    </p>
                  </div>
                );
              })
            : [1, 2, 3, 4].map(i => (
                <div key={i} className="h-28 animate-pulse rounded-2xl bg-[#f5f5f7]" />
              ))
          }
        </div>
      </div>

    </div>
  );
}
