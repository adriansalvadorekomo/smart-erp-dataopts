import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link } from "react-router-dom";
import { api, formatINR, formatPercent } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const STALE = 60_000;
const CAT_COLORS: Record<string, string> = {
  Electronics: "var(--primary)",
  Home: "#6e6e73",
  Sports: "#1d8127",
  Beauty: "#b25e09",
  Clothing: "#ff3b30",
};

function shortMonth(ym: string): string {
  return new Date(ym + "-01T00:00:00").toLocaleString("en-US", { month: "short" });
}

export default function Sales() {
  const trend = useQuery({ queryKey: ["cat-trend"], queryFn: () => api.categoryTrend(12), staleTime: STALE });
  const cities = useQuery({ queryKey: ["cities"], queryFn: api.cities, staleTime: STALE });
  const bands = useQuery({ queryKey: ["bands"], queryFn: api.bands, staleTime: STALE });
  const sellers = useQuery({ queryKey: ["sellers8"], queryFn: () => api.sellers(8), staleTime: STALE });

  // Pivot month × category → one row per month for the multi-line chart.
  const months: string[] = [];
  const byMonth: Record<string, Record<string, number>> = {};
  for (const r of trend.data ?? []) {
    if (!byMonth[r.month]) {
      byMonth[r.month] = {};
      months.push(r.month);
    }
    byMonth[r.month][r.category] = r.revenue;
  }
  months.sort();
  const series = months.map((m) => ({ month: m, ...byMonth[m] }));
  const cats = ["Electronics", "Home", "Sports", "Beauty", "Clothing"];
  const cityTotal = (cities.data ?? []).reduce((s, c) => s + c.revenue, 0);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-[32px] font-semibold tracking-tight">Sales</h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          What drives revenue — and what is changing.
        </p>
      </div>

      <Card className="border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle className="text-[15px] font-semibold">Category momentum · monthly revenue</CardTitle>
        </CardHeader>
        <CardContent className="h-72">
          {trend.data ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.6} />
                <XAxis
                  dataKey="month"
                  tickFormatter={shortMonth}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                  minTickGap={40}
                />
                <YAxis
                  tickFormatter={(v: number) => `₹${Math.round(v / 1e6)}M`}
                  tickLine={false}
                  axisLine={false}
                  width={56}
                  tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                />
                <Tooltip formatter={(v) => formatINR(Number(v), 0)} labelFormatter={(label) => shortMonth(String(label))} />
                <Legend wrapperStyle={{ fontSize: 13 }} />
                {cats.map((c) => (
                  <Line key={c} type="monotone" dataKey={c} stroke={CAT_COLORS[c]} strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[15px] text-muted-foreground">Loading…</p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-[15px] font-semibold">Revenue by region</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(cities.data ?? []).map((c) => (
              <div key={c.city} className="space-y-1.5">
                <div className="flex items-baseline justify-between text-[15px]">
                  <span className="font-medium">{c.city}</span>
                  <span className="text-muted-foreground tabular-nums">
                    {formatINR(c.revenue, 0)} · {formatPercent(c.revenue / (cityTotal || 1), 0)}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max((c.revenue / (cityTotal || 1)) * 100, 1.5)}%` }} />
                </div>
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
                  <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                    <div className="h-full rounded-full bg-secondary-foreground/70" style={{ width: `${Math.max((b.revenue / max) * 100, 1.5)}%` }} />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-[15px] font-semibold">Who drives revenue</CardTitle>
          <Link to="/sellers" className="text-[15px] text-primary hover:underline">
            All sellers →
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
    </div>
  );
}
