/**
 * Sales — Revenue drivers and growth trends.
 * No technical terms. Written for a business stakeholder.
 */
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  CartesianGrid, Legend,
  Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, formatINR, formatPercent, type CategoryTrendPoint } from "@/lib/api";

const STALE = 120_000;

const CATEGORY_COLORS: Record<string, string> = {
  Electronics: "#0071e3",
  Home:        "#34c759",
  Sports:      "#ff9f0a",
  Beauty:      "#ff375f",
  Clothing:    "#bf5af2",
};

function pivotTrend(rows: CategoryTrendPoint[]) {
  const byMonth: Record<string, Record<string, number>> = {};
  for (const r of rows) {
    if (!byMonth[r.month]) byMonth[r.month] = { month: r.month as never };
    byMonth[r.month][r.category] = r.revenue;
  }
  return Object.values(byMonth).sort((a, b) =>
    String(a.month).localeCompare(String(b.month))
  );
}

// ─── Primitives ───────────────────────────────────────────────────────────────

function Kpi({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5">
      <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">{label}</p>
      <p className="mt-3 text-[30px] font-semibold leading-none tracking-tight tabular-nums text-[#1d1d1f]">
        {value}
      </p>
      {note && <p className="mt-2 text-[13px] text-[#6e6e73]">{note}</p>}
    </div>
  );
}

function BarRow({
  label,
  value,
  note,
  share,
  color = "#0071e3",
  flag,
}: {
  label: string;
  value: string;
  note?: string;
  share: number;
  color?: string;
  flag?: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-4">
        <span className="flex items-center gap-2 text-[14px] font-medium text-[#1d1d1f]">
          {label}
          {flag && (
            <span className="rounded-full bg-[#ff3b30]/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#ff3b30]">
              {flag}
            </span>
          )}
        </span>
        <span className="shrink-0 tabular-nums text-[13px] text-[#6e6e73]">
          {value}
          {note && <span className="ml-2 text-[#aeaeb2]">{note}</span>}
        </span>
      </div>
      <div className="h-[3px] w-full overflow-hidden rounded-full bg-[#f5f5f7]">
        <div className="h-full rounded-full" style={{ width: `${Math.max(share * 100, 0.5)}%`, background: color }} />
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Sales() {
  const categories = useQuery({ queryKey: ["categories"],  queryFn: api.categories,    staleTime: STALE });
  const catTrend   = useQuery({ queryKey: ["catTrend"],    queryFn: api.categoryTrend, staleTime: STALE });
  const cities     = useQuery({ queryKey: ["cities"],      queryFn: api.salesByCity,   staleTime: STALE });
  const bands      = useQuery({ queryKey: ["bands"],       queryFn: api.discountBands, staleTime: STALE });
  const channels   = useQuery({ queryKey: ["channels"],    queryFn: api.channelMix,    staleTime: STALE });
  const overview   = useQuery({ queryKey: ["overview"],    queryFn: api.overview,      staleTime: STALE });

  const [trendView, setTrendView] = useState<"revenue" | "orders">("revenue");

  const o        = overview.data;
  const catTotal = (categories.data ?? []).reduce((s, c) => s + c.revenue, 0);
  const cityMax  = Math.max(...(cities.data ?? []).map(c => c.revenue), 1);
  const bandMax  = Math.max(...(bands.data ?? []).map(b => b.revenue), 1);
  const trendData = useMemo(() => (catTrend.data ? pivotTrend(catTrend.data) : []), [catTrend.data]);

  return (
    <div className="space-y-12">

      {/* Header */}
      <div className="border-b border-[#d2d2d7]/60 pb-6">
        <h1 className="text-[34px] font-semibold tracking-tight text-[#1d1d1f]">Sales</h1>
        <p className="mt-1 text-[15px] text-[#6e6e73]">
          Where revenue comes from and how it's growing
        </p>
      </div>

      {/* Top KPIs */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi
          label="Total revenue"
          value={o ? formatINR(o.revenue) : "—"}
          note={o ? `${o.total_orders.toLocaleString()} orders placed` : undefined}
        />
        <Kpi
          label="Avg. order value"
          value={o ? formatINR(o.aov) : "—"}
          note={o ? `Average discount applied: ${o.avg_discount_pct.toFixed(1)}%` : undefined}
        />
        <Kpi
          label="Electronics share"
          value={categories.data ? formatPercent(categories.data[0]?.revenue / catTotal) : "—"}
          note="of total revenue — highest category"
        />
        <Kpi
          label="Cities covered"
          value="5"
          note="Delhi · Bangalore · Mumbai · Chennai · Hyderabad"
        />
      </div>

      {/* Category trend — growth/decline over time */}
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Category performance over time</h2>
            <p className="mt-0.5 text-[13px] text-[#6e6e73]">
              Which product categories are growing or losing momentum?
            </p>
          </div>
          <div className="inline-flex rounded-full bg-[#f5f5f7] p-0.5">
            {(["revenue", "orders"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setTrendView(v)}
                className={`rounded-full px-3.5 py-1.5 text-[12px] font-medium capitalize transition-all ${
                  trendView === v
                    ? "bg-white text-[#1d1d1f] shadow-sm"
                    : "text-[#6e6e73] hover:text-[#1d1d1f]"
                }`}
              >
                By {v}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-6">
          <div className="h-64">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <CartesianGrid vertical={false} stroke="#e8e8ed" strokeOpacity={0.8} />
                  <XAxis
                    dataKey="month"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11, fill: "#6e6e73" }}
                    minTickGap={40}
                  />
                  <YAxis
                    tickFormatter={(v: number) =>
                      trendView === "revenue"
                        ? `₹${(v / 1e6).toFixed(0)}M`
                        : v.toLocaleString()
                    }
                    tickLine={false}
                    axisLine={false}
                    width={52}
                    tick={{ fontSize: 11, fill: "#6e6e73" }}
                  />
                  <Tooltip
                    formatter={(v, name) => [
                      trendView === "revenue"
                        ? formatINR(Number(v))
                        : Number(v).toLocaleString(),
                      name,
                    ]}
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid #d2d2d7",
                      borderRadius: "12px",
                      fontSize: "13px",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                    }}
                  />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: "12px", paddingTop: "12px" }}
                  />
                  {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
                    <Line
                      key={cat}
                      type="monotone"
                      dataKey={cat}
                      stroke={color}
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-[14px] text-[#6e6e73]">Loading…</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Category mix + City performance */}
      <div className="grid gap-6 lg:grid-cols-2">

        <div className="space-y-4">
          <div>
            <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Revenue by category</h2>
            <p className="mt-0.5 text-[13px] text-[#6e6e73]">
              Electronics leads on price, not volume — all categories sell similar quantities
            </p>
          </div>
          <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5 space-y-4">
            {(categories.data ?? []).map((c) => (
              <BarRow
                key={c.category}
                label={c.category}
                value={formatINR(c.revenue)}
                note={formatPercent(c.revenue / catTotal, 0)}
                share={c.revenue / catTotal}
                color={CATEGORY_COLORS[c.category] ?? "#6e6e73"}
              />
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Revenue by city</h2>
            <p className="mt-0.5 text-[13px] text-[#6e6e73]">
              Cities are near-equal in revenue. Bangalore and Chennai show higher return rates.
            </p>
          </div>
          <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5 space-y-4">
            {(cities.data ?? []).map((c) => (
              <BarRow
                key={c.city}
                label={c.city}
                value={formatINR(c.revenue)}
                note={`avg ${formatINR(c.aov)} / order`}
                share={c.revenue / cityMax}
                flag={c.return_rate > 0.115 ? "high returns" : undefined}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Discount impact + Channel mix */}
      <div className="grid gap-6 lg:grid-cols-2">

        <div className="space-y-4">
          <div>
            <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Impact of discounts</h2>
            <p className="mt-0.5 text-[13px] text-[#6e6e73]">
              Moderate discounts (10–30%) generate the most revenue. Deep discounts deliver less overall.
            </p>
          </div>
          <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5 space-y-4">
            {(bands.data ?? []).map((b) => (
              <BarRow
                key={b.band}
                label={`${b.band}% off`}
                value={formatINR(b.revenue)}
                note={`${b.lines.toLocaleString()} orders`}
                share={b.revenue / bandMax}
                color="#1d1d1f"
              />
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Sales by channel</h2>
            <p className="mt-0.5 text-[13px] text-[#6e6e73]">
              Payment methods and devices are evenly split. No channel shows unusual return behavior.
            </p>
          </div>
          {channels.data ? (
            <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5 space-y-6">
              <div className="space-y-3">
                <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
                  Payment method
                </p>
                {channels.data.payment.map((p) => {
                  const max = Math.max(...channels.data!.payment.map(x => x.revenue), 1);
                  return (
                    <BarRow
                      key={p.method}
                      label={p.method ?? ""}
                      value={`${p.orders.toLocaleString()} orders`}
                      note={`${formatPercent(p.return_rate)} returned`}
                      share={p.revenue / max}
                    />
                  );
                })}
              </div>
              <div className="space-y-3">
                <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
                  Device
                </p>
                {channels.data.device.map((d) => {
                  const max = Math.max(...channels.data!.device.map(x => x.revenue), 1);
                  return (
                    <BarRow
                      key={d.device}
                      label={d.device ?? ""}
                      value={`${d.orders.toLocaleString()} orders`}
                      note={`${formatPercent(d.return_rate)} returned`}
                      share={d.revenue / max}
                    />
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5">
              <p className="text-[14px] text-[#6e6e73]">Loading…</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
