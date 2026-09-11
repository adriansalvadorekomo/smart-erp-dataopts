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
import { api, formatINR, formatPercent, type DeliveryStatus } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusPill } from "@/components/StatusPill";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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

function Bar({ share, tone = "bg-primary" }: { share: number; tone?: string }) {
  return (
    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-secondary">
      <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.max(share * 100, 1.5)}%` }} />
    </div>
  );
}

function monthTick(date: string): string {
  const d = new Date(date + "T00:00:00");
  return d.toLocaleString("en-US", { month: "short" });
}

export default function Overview() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.overview, staleTime: STALE });
  const trend = useQuery({ queryKey: ["trend"], queryFn: () => api.trend(90), staleTime: STALE });
  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories, staleTime: STALE });
  const bands = useQuery({ queryKey: ["bands"], queryFn: api.bands, staleTime: STALE });
  const sellers = useQuery({ queryKey: ["sellers"], queryFn: () => api.topSellers(8), staleTime: STALE });
  const pareto = useQuery({ queryKey: ["pareto"], queryFn: api.pareto, staleTime: STALE });

  const o = overview.data;
  const catTotal = (categories.data ?? []).reduce((s, c) => s + c.revenue, 0);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-[32px] font-semibold tracking-tight">Overview</h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Gold KPIs over committed orders · business-model §5
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

      <Card className="border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle className="text-[15px] font-semibold">Revenue · trailing 90 days</CardTitle>
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

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-[15px] font-semibold">Revenue by category</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(categories.data ?? []).map((c) => (
              <div key={c.category} className="space-y-1.5">
                <div className="flex items-baseline justify-between text-[15px]">
                  <span className="font-medium">{c.category}</span>
                  <span className="text-muted-foreground tabular-nums">
                    {formatINR(c.revenue, 0)} · {formatPercent(c.revenue / (catTotal || 1), 0)}
                  </span>
                </div>
                <Bar share={c.revenue / (catTotal || 1)} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-[15px] font-semibold">Discount effectiveness</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(bands.data ?? []).map((b) => {
              const max = Math.max(...(bands.data ?? []).map((x) => x.revenue), 1);
              return (
                <div key={b.band} className="space-y-1.5">
                  <div className="flex items-baseline justify-between text-[15px]">
                    <span className="font-medium tabular-nums">{b.band}% off</span>
                    <span className="text-muted-foreground tabular-nums">
                      {formatINR(b.revenue, 0)} · {b.lines.toLocaleString()} lines
                    </span>
                  </div>
                  <Bar share={b.revenue / max} tone="bg-secondary-foreground/70" />
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-[15px] font-semibold">Top sellers</CardTitle>
          <Link to="/orders" className="text-[15px] text-primary hover:underline">
            All orders →
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs font-medium uppercase tracking-wide">Seller</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Lines</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Rating</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Revenue</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(sellers.data ?? []).map((s) => (
                <TableRow key={s.seller_id}>
                  <TableCell className="font-medium">{s.seller_id}</TableCell>
                  <TableCell className="text-right tabular-nums">{s.lines.toLocaleString()}</TableCell>
                  <TableCell className="text-right tabular-nums">{s.avg_rating.toFixed(1)}</TableCell>
                  <TableCell className="text-right font-medium tabular-nums">{formatINR(s.revenue, 0)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
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
    </div>
  );
}
