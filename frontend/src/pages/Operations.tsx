/**
 * Operations — Delivery performance and return analysis.
 * Written for a logistics/ops manager, not a data engineer.
 */
import { useQuery } from "@tanstack/react-query";
import {
  Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, formatPercent, type OpsRow } from "@/lib/api";

const STALE = 120_000;
const PLATFORM_RETURN = 0.116;

// ─── Primitives ───────────────────────────────────────────────────────────────

function Kpi({
  label, value, note, signal,
}: {
  label: string; value: string; note?: string; signal?: "bad" | "warn" | "good";
}) {
  const noteColor =
    signal === "bad"  ? "text-[#ff3b30]" :
    signal === "warn" ? "text-[#b25e09]" :
    signal === "good" ? "text-[#1d8127]" :
    "text-[#6e6e73]";
  return (
    <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5">
      <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">{label}</p>
      <p className="mt-3 text-[30px] font-semibold leading-none tracking-tight tabular-nums text-[#1d1d1f]">
        {value}
      </p>
      {note && <p className={`mt-2 text-[13px] ${noteColor}`}>{note}</p>}
    </div>
  );
}

function SectionHeader({ title, sub }: { title: string; sub: string }) {
  return (
    <div>
      <h2 className="text-[17px] font-semibold text-[#1d1d1f]">{title}</h2>
      <p className="mt-0.5 text-[13px] text-[#6e6e73]">{sub}</p>
    </div>
  );
}

/** Comparison table for return & delay rates across a dimension */
function BreakdownTable({
  rows,
  keyField,
  keyLabel,
}: {
  rows: OpsRow[];
  keyField: keyof OpsRow;
  keyLabel: string;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-[#d2d2d7]/60 bg-white">
      <table className="w-full">
        <thead>
          <tr className="border-b border-[#f5f5f7]">
            <th className="px-5 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
              {keyLabel}
            </th>
            <th className="px-5 py-3.5 text-right text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
              Orders
            </th>
            <th className="px-5 py-3.5 text-right text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
              Returned
            </th>
            <th className="px-5 py-3.5 text-right text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
              Delayed
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => {
            const key = String(r[keyField]);
            const highReturn = r.return_rate > PLATFORM_RETURN * 1.3;
            return (
              <tr key={key} className={idx > 0 ? "border-t border-[#f5f5f7]" : ""}>
                <td className="px-5 py-3 text-[14px] font-medium text-[#1d1d1f]">{key}</td>
                <td className="px-5 py-3 text-right text-[13px] tabular-nums text-[#6e6e73]">
                  {r.orders.toLocaleString()}
                </td>
                <td className={`px-5 py-3 text-right text-[13px] tabular-nums font-semibold ${highReturn ? "text-[#ff3b30]" : "text-[#6e6e73]"}`}>
                  {formatPercent(r.return_rate)}
                </td>
                <td className="px-5 py-3 text-right text-[13px] tabular-nums text-[#6e6e73]">
                  {formatPercent(r.delayed_rate)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Operations() {
  const ops      = useQuery({ queryKey: ["ops"],      queryFn: api.operationsBreakdown, staleTime: STALE });
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.overview,            staleTime: STALE });

  const o = overview.data;
  const d = ops.data;

  const shippingChart = (d?.by_shipping_days ?? []).map(r => ({
    label: `${r.shipping_time_days} day${r.shipping_time_days !== 1 ? "s" : ""}`,
    "Returned (%)":  +(r.return_rate  * 100).toFixed(1),
    "Delayed (%)":   +(r.delayed_rate * 100).toFixed(1),
  }));

  const sixDayReturn = d?.by_shipping_days.find(r => r.shipping_time_days === 6)?.return_rate ?? 0;
  const twoDayReturn = d?.by_shipping_days.find(r => r.shipping_time_days === 2)?.return_rate ?? 0;

  return (
    <div className="space-y-12">

      {/* Header */}
      <div className="border-b border-[#d2d2d7]/60 pb-6">
        <h1 className="text-[34px] font-semibold tracking-tight text-[#1d1d1f]">Operations</h1>
        <p className="mt-1 text-[15px] text-[#6e6e73]">
          Delivery performance, returns, and where problems are concentrated
        </p>
      </div>

      {/* Key finding */}
      {d && sixDayReturn > 0 && (
        <div className="rounded-2xl border border-[#b25e09]/30 bg-[#b25e09]/5 p-5">
          <p className="text-[13px] font-semibold text-[#b25e09]">Key finding</p>
          <p className="mt-1 text-[15px] text-[#1d1d1f]">
            Orders with 6-day shipping are returned at{" "}
            <strong className="text-[#ff3b30]">{formatPercent(sixDayReturn)}</strong>
            {" "}— nearly twice the rate of 2-day shipping ({formatPercent(twoDayReturn)}).
            The overall delay rate of ~50% appears across all segments, pointing to a
            systemic fulfillment issue rather than a specific category or city problem.
          </p>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi
          label="Return rate"
          value={o ? formatPercent(o.return_rate) : "—"}
          note="Platform baseline"
        />
        <Kpi
          label="Delivery delays"
          value={o ? formatPercent(o.delayed_rate) : "—"}
          note="of completed orders"
          signal="bad"
        />
        <Kpi
          label="6-day shipping returns"
          value={d ? formatPercent(sixDayReturn) : "—"}
          note={`vs ${formatPercent(twoDayReturn)} for 2-day`}
          signal="bad"
        />
        <Kpi
          label="Open shipments"
          value={o ? o.in_transit.toLocaleString() : "—"}
          note="orders in transit"
        />
      </div>

      {/* Shipping time chart */}
      <div className="space-y-4">
        <SectionHeader
          title="How shipping time affects returns"
          sub="Returns roughly double when delivery takes 6 days vs 1–3 days. Delay rate is flat across all shipping windows."
        />
        <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-6">
          <div className="h-56">
            {shippingChart.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={shippingChart} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <CartesianGrid vertical={false} stroke="#e8e8ed" strokeOpacity={0.8} />
                  <XAxis
                    dataKey="label"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: "#6e6e73" }}
                  />
                  <YAxis
                    tickFormatter={(v: number) => `${v}%`}
                    tickLine={false}
                    axisLine={false}
                    width={36}
                    tick={{ fontSize: 11, fill: "#6e6e73" }}
                    domain={[0, 60]}
                  />
                  <Tooltip
                    formatter={(v) => [`${v}%`]}
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid #d2d2d7",
                      borderRadius: "12px",
                      fontSize: "13px",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                    }}
                  />
                  <Bar dataKey="Returned (%)" radius={[3, 3, 0, 0]}>
                    {shippingChart.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={entry["Returned (%)"] > 15 ? "#ff3b30" : "#ff3b3055"}
                      />
                    ))}
                  </Bar>
                  <Bar dataKey="Delayed (%)" fill="#b25e09" fillOpacity={0.4} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-[14px] text-[#6e6e73]">Loading…</p>
              </div>
            )}
          </div>
          <div className="mt-3 flex gap-6 text-[12px] text-[#6e6e73]">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-3 rounded-sm bg-[#ff3b30]" /> Returned
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-3 rounded-sm bg-[#b25e09]/40" /> Delayed
            </span>
          </div>
        </div>
      </div>

      {/* Breakdown tables */}
      <div className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-3">
          <SectionHeader
            title="By product category"
            sub="Are returns concentrated in specific categories?"
          />
          {d && <BreakdownTable rows={d.by_category} keyField="category" keyLabel="Category" />}
        </div>
        <div className="space-y-3">
          <SectionHeader
            title="By city"
            sub="Bangalore, Chennai, and Hyderabad show slightly higher return rates."
          />
          {d && <BreakdownTable rows={d.by_city} keyField="city" keyLabel="City" />}
        </div>
        <div className="space-y-3">
          <SectionHeader
            title="By payment method"
            sub="No meaningful difference in returns across payment types."
          />
          {d && <BreakdownTable rows={d.by_payment} keyField="payment_method" keyLabel="Payment method" />}
        </div>
        <div className="space-y-3">
          <SectionHeader
            title="By shipping speed"
            sub="Slower deliveries return at significantly higher rates."
          />
          {d && (
            <div className="overflow-hidden rounded-2xl border border-[#d2d2d7]/60 bg-white">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#f5f5f7]">
                    <th className="px-5 py-3.5 text-left text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">Delivery time</th>
                    <th className="px-5 py-3.5 text-right text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">Orders</th>
                    <th className="px-5 py-3.5 text-right text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">Returned</th>
                    <th className="px-5 py-3.5 text-right text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">Delayed</th>
                  </tr>
                </thead>
                <tbody>
                  {d.by_shipping_days.map((r, idx) => {
                    const isHigh = r.return_rate > PLATFORM_RETURN * 1.5;
                    return (
                      <tr key={r.shipping_time_days} className={idx > 0 ? "border-t border-[#f5f5f7]" : ""}>
                        <td className="px-5 py-3 text-[14px] font-medium text-[#1d1d1f]">
                          {r.shipping_time_days} {r.shipping_time_days === 1 ? "day" : "days"}
                        </td>
                        <td className="px-5 py-3 text-right text-[13px] tabular-nums text-[#6e6e73]">
                          {r.orders.toLocaleString()}
                        </td>
                        <td className={`px-5 py-3 text-right text-[13px] tabular-nums font-semibold ${isHigh ? "text-[#ff3b30]" : "text-[#6e6e73]"}`}>
                          {formatPercent(r.return_rate)}
                        </td>
                        <td className="px-5 py-3 text-right text-[13px] tabular-nums text-[#6e6e73]">
                          {formatPercent(r.delayed_rate)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
