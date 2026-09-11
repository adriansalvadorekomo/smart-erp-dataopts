import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { ApiError, api, formatINR, type DeliveryStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
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

const TERMINALS: DeliveryStatus[] = ["DELIVERED", "DELAYED", "RETURNED"];

export default function OrderDetail() {
  const { id } = useParams();
  const orderId = Number(id);
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const order = useQuery({ queryKey: ["order", orderId], queryFn: () => api.getOrder(orderId) });
  const transition = useMutation({
    mutationFn: (to: DeliveryStatus) => api.transition(orderId, to),
    onSuccess: () => {
      setError(null);
      qc.invalidateQueries({ queryKey: ["order", orderId] });
      qc.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Transition failed"),
  });

  if (order.isLoading) return <p className="text-[15px] text-muted-foreground">Loading…</p>;
  if (order.isError || !order.data)
    return <p className="text-[15px] text-destructive">Order #{id} not found.</p>;
  const o = order.data;
  const total = o.items.reduce((t, i) => t + i.final_price, 0);
  const terminal = o.delivery_status !== "IN TRANSIT";

  return (
    <div className="space-y-6">
      <Link to="/orders" className="inline-flex items-center gap-1 text-[15px] text-primary hover:underline">
        <ArrowLeft size={16} /> Orders
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[32px] font-semibold tracking-tight tabular-nums">#{o.order_id}</h1>
          <p className="mt-1 text-[15px] text-muted-foreground">
            {o.customer_id} · {o.order_date} · {o.ship_to_city}
          </p>
          <p className="text-[13px] text-muted-foreground">
            {o.payment_method} · {o.device} · ships in {o.shipping_time_days}d
          </p>
        </div>
        <div className="text-right">
          <StatusPill status={o.delivery_status} />
          <p className="mt-2 text-[24px] font-semibold tracking-tight tabular-nums">{formatINR(total)}</p>
        </div>
      </div>

      <Card className="overflow-hidden border-border/60 shadow-sm">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs font-medium uppercase tracking-wide">Product</TableHead>
                <TableHead className="text-xs font-medium uppercase tracking-wide">Seller</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Qty</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Unit</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Disc.</TableHead>
                <TableHead className="text-right text-xs font-medium uppercase tracking-wide">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {o.items.map((i) => (
                <TableRow key={i.order_item_id}>
                  <TableCell className="font-medium">{i.product_id}</TableCell>
                  <TableCell className="text-muted-foreground">{i.seller_id}</TableCell>
                  <TableCell className="text-right tabular-nums">{i.quantity}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatINR(i.unit_price)}</TableCell>
                  <TableCell className="text-right tabular-nums">{i.discount_pct}%</TableCell>
                  <TableCell className="text-right font-medium tabular-nums">{formatINR(i.final_price)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {!terminal ? (
        <div className="flex items-center gap-2">
          <span className="text-[15px] text-muted-foreground">Mark as</span>
          {TERMINALS.map((t) => (
            <Button
              key={t}
              size="sm"
              variant="outline"
              className="rounded-full"
              disabled={transition.isPending}
              onClick={() => transition.mutate(t)}
            >
              {t.charAt(0) + t.slice(1).toLowerCase()}
            </Button>
          ))}
        </div>
      ) : (
        <p className="text-[13px] text-muted-foreground">
          Terminal state — immutable (business-model §3).
        </p>
      )}
      {error && <p className="text-[15px] text-destructive">{error}</p>}
    </div>
  );
}
