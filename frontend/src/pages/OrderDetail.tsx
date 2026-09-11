import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { ApiError, api, formatINR, type DeliveryStatus } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

  if (order.isLoading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (order.isError || !order.data)
    return <p className="text-sm text-destructive">Order #{id} not found.</p>;
  const o = order.data;
  const terminal = o.delivery_status !== "IN TRANSIT";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Order #{o.order_id}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {o.customer_id} · {o.order_date} · {o.ship_to_city} · {o.payment_method} · {o.device}
            </p>
          </div>
          <Badge variant={terminal ? "default" : "secondary"}>{o.delivery_status}</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead>Seller</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Unit</TableHead>
                <TableHead className="text-right">Disc %</TableHead>
                <TableHead className="text-right">Line total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {o.items.map((i) => (
                <TableRow key={i.order_item_id}>
                  <TableCell>{i.product_id}</TableCell>
                  <TableCell>{i.seller_id}</TableCell>
                  <TableCell className="text-right">{i.quantity}</TableCell>
                  <TableCell className="text-right">{formatINR(i.unit_price)}</TableCell>
                  <TableCell className="text-right">{i.discount_pct}%</TableCell>
                  <TableCell className="text-right">{formatINR(i.final_price)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {!terminal ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Transition to:</span>
              {TERMINALS.map((t) => (
                <Button key={t} size="sm" disabled={transition.isPending} onClick={() => transition.mutate(t)}>
                  {t}
                </Button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Terminal state — immutable (business-model §3).
            </p>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
