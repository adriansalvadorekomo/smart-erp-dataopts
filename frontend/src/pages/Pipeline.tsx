import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, XCircle } from "lucide-react";
import { Fragment } from "react";
import { Link } from "react-router-dom";
import { api, formatINR } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** Last full backfill validated on the workspace (docs/databricks-free-edition.md).
 * Static by design — the browser never holds workspace credentials. */
const BACKFILL = {
  at: "2026-09-11",
  bronze_rows: 1_000_000,
  revenue: 9938876984.9,
  silver: ["customers", "sellers", "products", "inventory", "orders", "order_items"],
  gold: ["fact_sales", "sales_daily", "customer_360", "inventory_kpis"],
};

function Stage({
  index,
  name,
  children,
}: {
  index: string;
  name: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="min-w-0 flex-1 border-border/60 shadow-sm">
      <CardHeader className="pb-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{index}</p>
        <CardTitle className="text-[17px] font-semibold tracking-tight">{name}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 text-[15px]">{children}</CardContent>
    </Card>
  );
}

function Num({ children }: { children: React.ReactNode }) {
  return <span className="font-semibold tabular-nums">{children}</span>;
}

export default function Pipeline() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: api.overview, staleTime: 60_000 });
  const dq = useQuery({ queryKey: ["dq"], queryFn: api.dqChecks, staleTime: 60_000 });
  const bad = (dq.data ?? []).filter((c) => c.violations > 0);
  const o = overview.data;

  const stages = [
    <Stage key="oltp" index="Source" name="PostgreSQL">
      <p><Num>{o ? o.total_orders.toLocaleString() : "—"}</Num> orders</p>
      <p className="text-muted-foreground">6 tables · live</p>
    </Stage>,
    <Stage key="bronze" index="Lakehouse" name="Bronze">
      <p><Num>{BACKFILL.bronze_rows.toLocaleString()}</Num> rows</p>
      <p className="text-muted-foreground">landing CSV · {BACKFILL.at}</p>
    </Stage>,
    <Stage key="silver" index="Lakehouse" name="Silver">
      <p><Num>{BACKFILL.silver.length}</Num> entities</p>
      <p className="text-muted-foreground">cleaned · typed</p>
    </Stage>,
    <Stage key="dq" index="Gate" name="DQ R1–R7">
      {dq.data ? (
        bad.length === 0 ? (
          <p className="inline-flex items-center gap-1.5 text-[15px] font-medium">
            <CheckCircle2 size={16} className="text-[var(--success)]" /> Passing
          </p>
        ) : (
          <p className="inline-flex items-center gap-1.5 text-[15px] font-medium text-destructive">
            <XCircle size={16} /> {bad.length} failing
          </p>
        )
      ) : (
        <p className="text-muted-foreground">Checking…</p>
      )}
      <p className="text-muted-foreground">over live OLTP</p>
    </Stage>,
    <Stage key="gold" index="Lakehouse" name="Gold">
      <p><Num>{BACKFILL.gold.length}</Num> marts</p>
      <p className="text-muted-foreground">{o ? formatINR(o.revenue, 0) : "—"} revenue</p>
    </Stage>,
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[32px] font-semibold tracking-tight">Pipeline</h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Is data flowing — source to Bronze to Silver through the gate to Gold.
        </p>
      </div>

      <div className="flex flex-col gap-2 xl:flex-row xl:items-stretch">
        {stages.map((s, i) => (
          <Fragment key={i}>
            {i > 0 && (
              <ArrowRight size={16} className="mx-auto shrink-0 self-center text-muted-foreground xl:mx-0" />
            )}
            {s}
          </Fragment>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-[15px] font-semibold">Silver entities</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-[15px] text-muted-foreground">{BACKFILL.silver.join(" · ")}</p>
          </CardContent>
        </Card>
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-[15px] font-semibold">Gold marts</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-[15px] text-muted-foreground">{BACKFILL.gold.join(" · ")}</p>
            <p className="mt-3 text-[15px]">
              <Link to="/operations" className="text-primary hover:underline">
                Rule-level gate status →
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
