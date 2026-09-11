import { useQuery } from "@tanstack/react-query";
import { api, formatINR, formatPercent } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { SellerPerf } from "@/lib/api";

function flags(s: SellerPerf): string[] {
  const out: string[] = [];
  if (s.avg_rating < 3.5) out.push("Low rating");
  if (s.delayed_rate > 0.6) out.push("Delays");
  if (s.return_rate > 0.2) out.push("Returns");
  return out;
}

export default function Sellers() {
  const sellers = useQuery({ queryKey: ["sellers50"], queryFn: () => api.sellers(50), staleTime: 60_000 });
  const rows = sellers.data ?? [];
  const flagged = rows.filter((s) => flags(s).length > 0);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[32px] font-semibold tracking-tight">Sellers</h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Who performs — and who needs attention.{" "}
          {rows.length > 0 && (
            <span className="font-medium text-foreground">
              {flagged.length} of {rows.length} flagged
            </span>
          )}
        </p>
      </div>

      <Card className="overflow-hidden border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle className="text-[15px] font-semibold">Performance · top 50 by revenue</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs font-medium uppercase tracking-wide">Seller</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Revenue</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Lines</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Rating</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Delayed</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Returned</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Attention</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((s) => {
                const f = flags(s);
                return (
                  <TableRow key={s.seller_id} className={cn(f.length > 0 && "bg-destructive/[0.04]")}>
                    <TableCell className="font-medium">{s.seller_id}</TableCell>
                    <TableCell className="text-right font-medium tabular-nums">{formatINR(s.revenue, 0)}</TableCell>
                    <TableCell className="text-right tabular-nums">{s.lines.toLocaleString()}</TableCell>
                    <TableCell className={cn("text-right tabular-nums", s.avg_rating < 3.5 ? "font-semibold text-destructive" : "text-muted-foreground")}>
                      {s.avg_rating.toFixed(1)}
                    </TableCell>
                    <TableCell className={cn("text-right tabular-nums", s.delayed_rate > 0.6 ? "font-semibold text-destructive" : "text-muted-foreground")}>
                      {formatPercent(s.delayed_rate, 0)}
                    </TableCell>
                    <TableCell className={cn("text-right tabular-nums", s.return_rate > 0.2 ? "font-semibold text-destructive" : "text-muted-foreground")}>
                      {formatPercent(s.return_rate, 0)}
                    </TableCell>
                    <TableCell className="text-right">
                      {f.length > 0 ? (
                        <span className="text-[13px] font-medium text-destructive">{f.join(" · ")}</span>
                      ) : (
                        <span className="text-[13px] text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
