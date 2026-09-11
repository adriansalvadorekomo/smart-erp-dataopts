/**
 * Sellers — Seller performance and quality risks.
 * Written for a marketplace manager, not a data analyst.
 */
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  CartesianGrid, ResponsiveContainer, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis, ReferenceLine,
} from "recharts";
import { api, formatINR, formatPercent } from "@/lib/api";

const STALE = 120_000;
const PLATFORM_RETURN = 0.116;
const RISK_THRESHOLD  = PLATFORM_RETURN * 1.5; // 17.4%

type SortKey = "revenue" | "return_rate" | "avg_rating";
const SORT_LABELS: Record<SortKey, string> = {
  revenue:     "Revenue",
  return_rate: "Return rate",
  avg_rating:  "Rating",
};

// ─── Primitives ───────────────────────────────────────────────────────────────

function Kpi({ label, value, note, signal }: {
  label: string; value: string; note?: string;
  signal?: "bad" | "warn" | "good";
}) {
  const noteColor =
    signal === "bad"  ? "text-[#ff3b30]" :
    signal === "warn" ? "text-[#b25e09]" :
    signal === "good" ? "text-[#1d8127]" :
    "text-[#6e6e73]";
  return (
    <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5">
      <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">{label}</p>
      <p className="mt-3 text-[30px] font-semibold leading-none tracking-tight tabular-nums text-[#1d1d1f]">{value}</p>
      {note && <p className={`mt-2 text-[13px] ${noteColor}`}>{note}</p>}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Sellers() {
  const sellers  = useQuery({ queryKey: ["sellerPerf"], queryFn: () => api.sellerPerformance(50), staleTime: STALE });
  const overview = useQuery({ queryKey: ["overview"],   queryFn: api.overview,                   staleTime: STALE });

  const [sort,   setSort]   = useState<SortKey>("revenue");
  const [filter, setFilter] = useState<"all" | "at-risk">("all");

  const data = sellers.data ?? [];
  const o    = overview.data;

  const riskSellers = data.filter(s => s.return_rate > RISK_THRESHOLD);
  const top5Revenue = data.slice(0, 5).reduce((s, r) => s + r.revenue, 0);

  const sorted = useMemo(() => {
    const base = filter === "at-risk" ? riskSellers : data;
    return [...base].sort((a, b) => {
      if (sort === "revenue")     return b.revenue - a.revenue;
      if (sort === "return_rate") return b.return_rate - a.return_rate;
      return a.avg_rating - b.avg_rating;
    });
  }, [data, riskSellers, sort, filter]);

  const scatterData = data.map(s => ({
    revenue:     s.revenue,
    return_pct:  +(s.return_rate * 100).toFixed(2),
    seller_id:   s.seller_id,
    avg_rating:  s.avg_rating,
    at_risk:     s.return_rate > RISK_THRESHOLD,
  }));

  return (
    <div className="space-y-12">

      {/* Header */}
      <div className="border-b border-[#d2d2d7]/60 pb-6">
        <h1 className="text-[34px] font-semibold tracking-tight text-[#1d1d1f]">Sellers</h1>
        <p className="mt-1 text-[15px] text-[#6e6e73]">
          Revenue performance, quality signals, and sellers that need attention
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Sellers analyzed" value={data.length.toLocaleString()} note="10+ orders minimum" />
        <Kpi
          label="Top seller revenue"
          value={data[0] ? formatINR(data[0].revenue) : "—"}
          note={data[0]?.seller_id}
        />
        <Kpi
          label="Top 5 revenue share"
          value={formatPercent(top5Revenue / (o?.revenue ?? 1))}
          note="of all revenue"
          signal={top5Revenue / (o?.revenue ?? 1) > 0.05 ? "warn" : undefined}
        />
        <Kpi
          label="Sellers needing review"
          value={riskSellers.length.toString()}
          note={`return rate above ${formatPercent(RISK_THRESHOLD)}`}
          signal={riskSellers.length > 0 ? "bad" : "good"}
        />
      </div>

      {/* Scatter: Revenue vs Return rate */}
      <div className="space-y-4">
        <div>
          <h2 className="text-[17px] font-semibold text-[#1d1d1f]">
            Revenue vs return rate
          </h2>
          <p className="mt-0.5 text-[13px] text-[#6e6e73]">
            Sellers in the top-right — high revenue and high returns — are your biggest quality risk.
            The red line marks {formatPercent(RISK_THRESHOLD)} (1.5× the platform average).
          </p>
        </div>
        <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-6">
          <div className="h-64">
            {scatterData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="#e8e8ed" strokeOpacity={0.8} />
                  <XAxis
                    type="number"
                    dataKey="revenue"
                    tickFormatter={(v: number) => formatINR(v)}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: "#6e6e73" }}
                    name="Revenue"
                  />
                  <YAxis
                    type="number"
                    dataKey="return_pct"
                    tickFormatter={(v: number) => `${v}%`}
                    tickLine={false}
                    axisLine={false}
                    width={36}
                    tick={{ fontSize: 11, fill: "#6e6e73" }}
                    name="Return rate"
                  />
                  <ReferenceLine
                    y={RISK_THRESHOLD * 100}
                    stroke="#ff3b30"
                    strokeDasharray="4 2"
                    strokeOpacity={0.6}
                  />
                  <Tooltip
                    cursor={{ strokeDasharray: "3 3", stroke: "#d2d2d7" }}
                    content={({ payload }) => {
                      if (!payload?.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="rounded-xl border border-[#d2d2d7] bg-white px-3 py-2.5 text-[13px] shadow-sm">
                          <p className="font-semibold text-[#1d1d1f]">{d.seller_id}</p>
                          <p className="text-[#6e6e73]">Revenue: {formatINR(d.revenue)}</p>
                          <p className={d.at_risk ? "font-semibold text-[#ff3b30]" : "text-[#6e6e73]"}>
                            Returns: {d.return_pct}%
                          </p>
                          <p className="text-[#6e6e73]">Rating: {d.avg_rating.toFixed(1)}</p>
                        </div>
                      );
                    }}
                  />
                  <Scatter
                    data={scatterData}
                    shape={(props: { cx?: number; cy?: number; payload?: { at_risk: boolean } }) => {
                      const { cx = 0, cy = 0, payload } = props;
                      return (
                        <circle
                          cx={cx} cy={cy} r={4}
                          fill={payload?.at_risk ? "#ff3b30" : "#0071e3"}
                          fillOpacity={0.65}
                        />
                      );
                    }}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-[14px] text-[#6e6e73]">Loading…</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Seller table */}
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Seller rankings</h2>
            <p className="mt-0.5 text-[13px] text-[#6e6e73]">Top 50 sellers · use the filters to find quality risks</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {/* Risk filter */}
            <div className="inline-flex rounded-full bg-[#f5f5f7] p-0.5">
              {(["all", "at-risk"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-full px-3.5 py-1.5 text-[12px] font-medium transition-all ${
                    filter === f ? "bg-white text-[#1d1d1f] shadow-sm" : "text-[#6e6e73] hover:text-[#1d1d1f]"
                  }`}
                >
                  {f === "at-risk" ? "⚠ Needs review" : "All sellers"}
                </button>
              ))}
            </div>
            {/* Sort */}
            <div className="inline-flex rounded-full bg-[#f5f5f7] p-0.5">
              {(Object.entries(SORT_LABELS) as [SortKey, string][]).map(([k, label]) => (
                <button
                  key={k}
                  onClick={() => setSort(k)}
                  className={`rounded-full px-3 py-1.5 text-[12px] font-medium transition-all ${
                    sort === k ? "bg-white text-[#1d1d1f] shadow-sm" : "text-[#6e6e73] hover:text-[#1d1d1f]"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#d2d2d7]/60 bg-white">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#f5f5f7]">
                {["Seller", "Orders", "Revenue", "Rating", "Return rate", "Delay rate"].map((h, i) => (
                  <th
                    key={h}
                    className={`px-5 py-3.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73] ${
                      i === 0 ? "text-left" : "text-right"
                    }`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((s, idx) => {
                const isRisk = s.return_rate > RISK_THRESHOLD;
                return (
                  <tr
                    key={s.seller_id}
                    className={`${idx > 0 ? "border-t border-[#f5f5f7]" : ""} ${isRisk ? "bg-[#ff3b30]/2" : ""}`}
                  >
                    <td className="px-5 py-3 text-[14px] font-semibold text-[#1d1d1f]">
                      {s.seller_id}
                      {isRisk && (
                        <span className="ml-2 rounded-full bg-[#ff3b30]/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#ff3b30]">
                          review
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right text-[13px] tabular-nums text-[#6e6e73]">
                      {s.orders.toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right text-[14px] font-semibold tabular-nums text-[#1d1d1f]">
                      {formatINR(s.revenue)}
                    </td>
                    <td className="px-5 py-3 text-right text-[13px] tabular-nums text-[#6e6e73]">
                      {s.avg_rating.toFixed(1)} / 5
                    </td>
                    <td className={`px-5 py-3 text-right text-[13px] tabular-nums ${isRisk ? "font-semibold text-[#ff3b30]" : "text-[#6e6e73]"}`}>
                      {formatPercent(s.return_rate)}
                    </td>
                    <td className="px-5 py-3 text-right text-[13px] tabular-nums text-[#6e6e73]">
                      {formatPercent(s.delayed_rate)}
                    </td>
                  </tr>
                );
              })}
              {sorted.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-[14px] text-[#6e6e73]">
                    No sellers match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
