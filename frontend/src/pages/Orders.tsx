import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { api, formatINR, type DeliveryStatus } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { StatusPill } from "@/components/StatusPill";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const FILTERS: (DeliveryStatus | "ALL")[] = ["ALL", "IN TRANSIT", "DELIVERED", "DELAYED", "RETURNED"];

export default function Orders() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  const orders = useQuery({
    queryKey: ["orders", filter],
    queryFn: () =>
      api.listOrders(filter === "ALL" ? undefined : { delivery_status: filter }),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight">Orders</h1>
          <p className="mt-1 text-[15px] text-muted-foreground">
            {orders.data ? `${orders.data.length} shown · latest first` : "Latest first"}
          </p>
        </div>
        <Link
          to="/new"
          className="rounded-full bg-primary px-4 py-2 text-[15px] font-medium text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
        >
          New order
        </Link>
      </div>

      <div className="inline-flex rounded-full bg-secondary p-1">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={cn(
              "rounded-full px-3.5 py-1.5 text-[13px] font-medium capitalize transition-all",
              filter === f
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {f === "ALL" ? "All" : f.charAt(0) + f.slice(1).toLowerCase()}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden border-border/60 shadow-sm">
        <CardContent className="p-0">
          {orders.isError ? (
            <p className="p-6 text-[15px] text-destructive">
              Couldn't load orders. Is the backend running?
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="text-xs font-medium uppercase tracking-wide">Order</TableHead>
                  <TableHead className="text-xs font-medium uppercase tracking-wide">Customer</TableHead>
                  <TableHead className="text-xs font-medium uppercase tracking-wide">Date</TableHead>
                  <TableHead className="text-xs font-medium uppercase tracking-wide">Status</TableHead>
                  <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(orders.data ?? []).map((o) => (
                  <TableRow key={o.order_id}>
                    <TableCell className="font-medium">
                      <Link className="text-primary hover:underline" to={`/orders/${o.order_id}`}>
                        #{o.order_id}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{o.customer_id}</TableCell>
                    <TableCell className="text-muted-foreground tabular-nums">{o.order_date}</TableCell>
                    <TableCell>
                      <StatusPill status={o.delivery_status} />
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatINR(o.items.reduce((t, i) => t + i.final_price, 0))}
                    </TableCell>
                  </TableRow>
                ))}
                {orders.data?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-10 text-center text-muted-foreground">
                      No orders here yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
