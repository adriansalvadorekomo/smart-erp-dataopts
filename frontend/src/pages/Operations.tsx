import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";
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

export default function Operations() {
  const cities = useQuery({ queryKey: ["cities"], queryFn: api.cities, staleTime: STALE });
  const stock = useQuery({ queryKey: ["stock"], queryFn: () => api.stockCritical(50), staleTime: STALE });
  const dq = useQuery({ queryKey: ["dq"], queryFn: api.dqChecks, staleTime: STALE });
  const bad = (dq.data ?? []).filter((c) => c.violations > 0);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-[32px] font-semibold tracking-tight">Operations</h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          What needs action — fulfillment, inventory, data quality.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-[15px] font-semibold">Shipping performance by region</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(cities.data ?? []).map((c) => (
              <div key={c.city} className="flex items-baseline justify-between gap-4 text-[15px]">
                <span className="font-medium">{c.city}</span>
                <span className="text-muted-foreground tabular-nums">
                  {formatPercent(c.delayed_rate, 0)} delayed · {formatPercent(c.return_rate, 0)} returned
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-[15px] font-semibold">DQ gate over live data</CardTitle>
            {dq.data &&
              (bad.length === 0 ? (
                <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[var(--success)]">
                  <CheckCircle2 size={14} /> Passing
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-destructive">
                  <XCircle size={14} /> {bad.length} failing
                </span>
              ))}
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableBody>
                {(dq.data ?? []).map((c) => (
                  <TableRow key={c.rule}>
                    <TableCell className="font-medium">{c.rule}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {c.violations === 0 ? (
                        <span className="inline-flex items-center gap-1 text-[var(--success)]">
                          <CheckCircle2 size={14} /> 0
                        </span>
                      ) : (
                        <span className="font-semibold text-destructive">{c.violations.toLocaleString()}</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-[15px] font-semibold">
            Reorder now · {(stock.data ?? []).length > 0 ? "lowest stock first" : ""}
          </CardTitle>
          <Link to="/orders" className="text-[15px] text-primary hover:underline">
            Orders →
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs font-medium uppercase tracking-wide">Product</TableHead>
                <TableHead className="text-xs font-medium uppercase tracking-wide">Category</TableHead>
                <TableHead className="text-xs font-medium uppercase tracking-wide">Brand</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Price</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Stock</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(stock.data ?? []).map((p) => (
                <TableRow key={p.product_id}>
                  <TableCell className="font-medium">{p.product_id}</TableCell>
                  <TableCell className="text-muted-foreground">{p.category}</TableCell>
                  <TableCell className="text-muted-foreground">{p.brand}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatINR(p.current_price, 0)}</TableCell>
                  <TableCell className="text-right font-semibold tabular-nums text-destructive">
                    {p.latest_stock}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
