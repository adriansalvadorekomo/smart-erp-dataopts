/**
 * Overview — business health at a glance.
 * Every label is written for a non-technical stakeholder.
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import {
  Area, AreaChart, CartesianGrid,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, formatINR, formatPercent } from "@/lib/api";

const STALE = 60_000;

// ─── KPI card ─────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  note,
  signal,
  href,
}: {
  label: string;
  value: string;
  note?: string;
  signal?: "warn" | "bad" | "good";
  href?: string;
}) {
  const noteColor =
    signal === "bad"  ? "text-[#ff3b30]" :
    signal === "warn" ? "text-[#b25e09]" :
    signal === "good" ? "text-[#1d8127]" :
    "text-[#6e6e73]";

  const inner = (
    <div className="flex h-full flex-col justify-between rounded-2xl border border-[#d2d2d7]/60 bg-white p-5 transition-shadow hover:shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
      <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
        {label}
      </p>
      <div>
        <p className="mt-3 text-[30px] font-semibold leading-none tracking-tight tabular-nums text-[#1d1d1f]">
          {value}
        </p>
        {note && (
          <p className={`mt-2 text-[13px] ${noteColor}`}>{note}</p>
        )}
      </div>
    </div>
  );

  return href ? (
    <Link to={href} className="block h-full">{inner}</Link>
  ) : (
    inner
  );
}

// ─── Section title ────────────────────────────────────────────────────────────

function SectionTitle({
  title,
  sub,
  link,
  linkTo,
}: {
  title: string;
  sub?: string;
  link?: string;
  linkTo?: string;
}) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h2 className="text-[17px] font-semibold text-[#1d1d1f]">{title}</h2>
        {sub && <p className="mt-0.5 text-[13px] text-[#6e6e73]">{sub}</p>}
      </div>
      {link && linkTo && (
        <Link
          to={linkTo}
          className="flex shrink-0 items-center gap-1 text-[13px] font-medium text-[#0071e3] hover:underline"
        >
          {link} <ArrowUpRight size={13} />
        </Link>
      )}
    </div>
  );
}

// ─── Row bar ─────────────────────────────────────────────────────────────────

function BarRow({
  label,
  value,
  note,
  share,
  color = "#0071e3",
  tag,
}: {
  label: string;
  value: string;
  note?: string;
  share: number;
  color?: string;
  tag?: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-4">
        <span className="flex items-center gap-2 text-[14px] font-medium text-[#1d1d1f]">
          {label}
          {tag && (
            <span className="rounded-full bg-[#ff3b30]/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#ff3b30]">
              {tag}
            </span>
          )}
        </span>
        <span className="shrink-0 text-[13px] tabular-nums text-[#6e6e73]">
          {value}
          {note && <span className="ml-2 text-[#aeaeb2]">{note}</span>}
        </span>
      </div>
      <div className="h-[3px] w-full overflow-hidden rounded-full bg-[#f5f5f7]">
        <div
          className="h-full rounded-full"
          style={{ width: `${Math.max(share * 100, 0.5)}%`, background: color }}
        />
      </div>
    </div>
  );
}

function monthLabel(date: string) {
  return new Date(date + "T00:00:00").toLocaleString("en-US", { month: "short" });
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Overview() {
  const overview = useQuery({ queryKey: ["overview"],  queryFn: api.overview,    staleTime: STALE });
  const trend    = useQuery({ queryKey: ["trend"],     queryFn: () => api.trend(90), staleTime: STALE });
  const cities   = useQuery({ queryKey: ["cities"],    queryFn: api.salesByCity, staleTime: STALE });
  const pareto   = useQuery({ queryKey: ["pareto"],    queryFn: api.pareto,      staleTime: STALE });

  const o = overview.data;
  const cityMax = Math.max(...(cities.data ?? []).map(c => c.revenue), 1);

  const STATUS_ORDER = ["DELIVERED", "IN TRANSIT", "DELAYED", "RETURNED"] as const;
  const STATUS_LABEL: Record<string, string> = {
    "DELIVERED":   "Delivered",
    "IN TRANSIT":  "In transit",
    "DELAYED":     "Delayed",
    "RETURNED":    "Returned",
  };
  const STATUS_COLOR: Record<string, string> = {
    "DELIVERED":  "#1d8127",
    "IN TRANSIT": "#0071e3",
    "DELAYED":    "#b25e09",
    "RETURNED":   "#ff3b30",
  };

  return (
    <div className="space-y-12">

      {/* Page header */}
      <div className="border-b border-[#d2d2d7]/60 pb-6">
        <h1 className="text-[34px] font-semibold tracking-tight text-[#1d1d1f]">
          Overview
        </h1>
        <p className="mt-1 text-[15px] text-[#6e6e73]">
          Business health snapshot · India marketplace · 24-month view
        </p>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="Total revenue"
          value={o ? formatINR(o.revenue) : "—"}
          note={o ? `From ${o.total_orders.toLocaleString()} orders` : undefined}
        />
        <KpiCard
          label="Avg. order value"
          value={o ? formatINR(o.aov) : "—"}
          note={o ? `Average discount ${o.avg_discount_pct.toFixed(1)}%` : undefined}
        />
        <KpiCard
          label="Return rate"
          value={o ? formatPercent(o.return_rate) : "—"}
          note={o ? `${Math.round(o.return_rate * o.total_orders).toLocaleString()} orders returned` : undefined}
          href="/operations"
        />
        <KpiCard
          label="Delivery delays"
          value={o ? formatPercent(o.delayed_rate) : "—"}
          note="of completed orders"
          signal="bad"
          href="/operations"
        />
        <KpiCard
          label="Open orders"
          value={o ? o.in_transit.toLocaleString() : "—"}
          note="currently being shipped"
        />
        <KpiCard
          label="Low stock products"
          value={o ? o.stock_critical.toLocaleString() : "—"}
          note="fewer than 20 units remaining"
          signal={o && o.stock_critical > 3000 ? "warn" : "good"}
        />
        <KpiCard
          label="Top customer share"
          value={pareto.data ? formatPercent(pareto.data.top20_share) : "—"}
          note="Top 20% of customers"
          signal="warn"
        />
        <KpiCard
          label="Active customers"
          value="603,815"
          note="across 5 cities"
        />
      </div>

      {/* Revenue trend */}
      <div className="space-y-4">
        <SectionTitle
          title="Revenue trend"
          sub="Daily revenue over the last 90 days"
          link="Sales detail"
          linkTo="/sales"
        />
        <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-6">
          <div className="h-52">
            {trend.data && trend.data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend.data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0071e3" stopOpacity={0.12} />
                      <stop offset="100%" stopColor="#0071e3" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="#e8e8ed" strokeOpacity={0.8} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={monthLabel}
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: "#6e6e73" }}
                    minTickGap={48}
                  />
                  <YAxis
                    tickFormatter={(v: number) =>
                      v >= 1e6 ? `₹${(v / 1e6).toFixed(0)}M` : `₹${v}`
                    }
                    tickLine={false}
                    axisLine={false}
                    width={52}
                    tick={{ fontSize: 11, fill: "#6e6e73" }}
                  />
                  <Tooltip
                    formatter={(v) => [formatINR(Number(v)), "Revenue"]}
                    labelFormatter={(d) => String(d)}
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid #d2d2d7",
                      borderRadius: "12px",
                      fontSize: "13px",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                    }}
                    cursor={{ stroke: "#0071e3", strokeWidth: 1, strokeOpacity: 0.3 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#0071e3"
                    strokeWidth={2}
                    fill="url(#revGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-[14px] text-[#6e6e73]">Loading…</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Two columns: cities + order status */}
      <div className="grid gap-6 lg:grid-cols-2">

        {/* Revenue by city */}
        <div className="space-y-4">
          <SectionTitle
            title="Revenue by city"
            sub="Which markets are performing best?"
            link="Full breakdown"
            linkTo="/sales"
          />
          <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5 space-y-4">
            {cities.data
              ? cities.data.map((c) => (
                  <BarRow
                    key={c.city}
                    label={c.city}
                    value={formatINR(c.revenue)}
                    note={`avg ${formatINR(c.aov)} / order`}
                    share={c.revenue / cityMax}
                    tag={c.return_rate > 0.115 ? "high returns" : undefined}
                  />
                ))
              : <p className="py-4 text-center text-[14px] text-[#6e6e73]">Loading…</p>
            }
          </div>
        </div>

        {/* Order status breakdown */}
        <div className="space-y-4">
          <SectionTitle
            title="Order status"
            sub="Current state of all orders placed"
            link="Delivery issues"
            linkTo="/operations"
          />
          <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5 space-y-4">
            {o
              ? STATUS_ORDER
                  .filter(s => o.by_status[s] !== undefined)
                  .map((status) => {
                    const n = o.by_status[status] ?? 0;
                    return (
                      <BarRow
                        key={status}
                        label={STATUS_LABEL[status]}
                        value={n.toLocaleString()}
                        note={formatPercent(n / o.total_orders)}
                        share={n / o.total_orders}
                        color={STATUS_COLOR[status]}
                        tag={
                          status === "DELAYED"
                            ? "needs attention"
                            : undefined
                        }
                      />
                    );
                  })
              : <p className="py-4 text-center text-[14px] text-[#6e6e73]">Loading…</p>
            }
          </div>
        </div>

      </div>
    </div>
  );
}
