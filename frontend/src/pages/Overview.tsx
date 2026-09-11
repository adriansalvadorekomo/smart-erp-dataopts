import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { api, formatINR, formatPercent, type DeliveryStatus } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusPill } from "@/components/StatusPill";

const STALE = 60_000;

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <p className="text-[13px] font-medium text-muted-foreground">{label}</p>
      <p className="mt-1 text-[28px] font-semibold tracking-tight tabular-nums">{value}</p>
      {sub && <p className="mt-0.5 text-[13px] text-muted-foreground tabular-nums">{sub}</p>}
    </div>
  );
}

function monthTick(date: string): string {
  return new Date(date + "T00:00:00").toLocaleString("en-US", { month: "short" });
}

export default function Overview() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.overview, staleTime: STALE });
  const trend = useQuery({ queryKey: ["trend"], queryFn: () => api.trend(90), staleTime: STALE });
  const pareto = useQuery({ queryKey: ["pareto"], queryFn: api.pareto, staleTime: STALE });
  const cities = useQuery({ queryKey: ["cities"], queryFn: api.cities, staleTime: STALE });
  const sellers = useQuery({ queryKey: ["sellers-att"], queryFn: () => api.sellers(20), staleTime: STALE });

  const o = overview.data;
  const worstCity = [...(cities.data ?? [])].sort((a, b) => b.delayed_rate - a.delayed_rate)[0];
  const worstSeller = [...(sellers.data ?? [])].sort((a, b) => b.return_rate - a.return_rate)[0];
  const attention = [
    o && o.stock_critical > 0
      ? { text: `${o.stock_critical.toLocaleString()} products need reordering`, to: "/operations" }
      : null,
    worstCity
      ? { text: `${worstCity.city} delays ${formatPercent(worstCity.delayed_rate, 0)} of completed orders`, to: "/operations" }
      : null,
    worstSeller && worstSeller.return_rate > 0
      ? { text: `${worstSeller.seller_id} returns ${formatPercent(worstSeller.return_rate, 0)} of lines`, to: "/sellers" }
      : null,
  ].filter((a): a is { text: string; to: string } => a !== null);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-[32px] font-semibold tracking-tight">Overview</h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          The business pulse — Gold KPIs over committed orders.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-8 lg:grid-cols-4">
        <Kpi label="Revenue" value={o ? formatINR(o.revenue, 0) : "—"} sub={o ? `${o.total_orders.toLocaleString()} orders` : undefined} />
        <Kpi label="Avg order value" value={o ? formatINR(o.aov, 0) : "—"} sub={o ? `Ø ${o.avg_discount_pct.toFixed(1)}% discount` : undefined} />
        <Kpi label="Return rate" value={o ? formatPercent(o.return_rate) : "—"} sub={o ? `${o.in_transit.toLocaleString()} in transit` : undefined} />
        <Kpi label="Delayed rate" value={o ? formatPercent(o.delayed_rate) : "—"} sub="of completed orders" />
        <Kpi label="Stock-critical" value={o ? o.stock_critical.toLocaleString() : "—"} sub="latest stock < 20" />
        <Kpi
          label="Top 20% share"
          value={pareto.data ? formatPercent(pareto.data.top20_share) : "—"}
          sub="of revenue (Pareto)"
        />
      </div>

      {attention.length > 0 && (
        <Card className="border-border/60 shadow-sm">
          <CardContent className="divide-y divide-border/60 p-0">
            {attention.map((a) => (
              <Link key={a.text} to={a.to} className="flex items-center justify-between px-6 py-3.5 transition-colors hover:bg-muted/50">
                <span className="text-[15px] font-medium">{a.text}</span>
                <ArrowUpRight size={16} className="text-muted-foreground" />
              </Link>
            ))}
          </CardContent>
        </Card>
      )}

      <Card className="border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle className="text-[15px] font-semibold">Revenue · last 90 selling days</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          {trend.data ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trend.data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.6} />
                <XAxis
                  dataKey="date"
                  tickFormatter={monthTick}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                  minTickGap={32}
                />
                <YAxis
                  tickFormatter={(v: number) => `₹${Math.round(v / 1e6)}M`}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                  tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                />
                <Tooltip
                  formatter={(v) => [formatINR(Number(v)), "Revenue"]}
                  labelFormatter={(d) => String(d)}
                />
                <Area type="monotone" dataKey="revenue" stroke="var(--primary)" strokeWidth={2} fill="var(--primary)" fillOpacity={0.12} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[15px] text-muted-foreground">Loading…</p>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        {(o ? Object.entries(o.by_status) : []).map(([status, n]) => (
          <span key={status} className="inline-flex items-center gap-2 text-[13px] text-muted-foreground">
            <StatusPill status={status as DeliveryStatus} />
            <span className="tabular-nums">{n.toLocaleString()}</span>
          </span>
        ))}
      </div>

      <p className="text-[13px] text-muted-foreground">
        Revenue drivers live under <Link to="/sales" className="text-primary hover:underline">Sales</Link> ·
        seller quality under <Link to="/sellers" className="text-primary hover:underline">Sellers</Link>
      </p>
    </div>
  );
}
