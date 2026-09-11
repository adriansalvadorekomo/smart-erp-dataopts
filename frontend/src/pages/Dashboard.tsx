import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PackageSearch } from "lucide-react";
import { api, formatINR, type DeliveryStatus } from "@/lib/api";
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
import { useState } from "react";

const STATUS_VARIANT: Record<DeliveryStatus, "default" | "secondary" | "destructive" | "outline"> = {
  "IN TRANSIT": "secondary",
  DELIVERED: "default",
  DELAYED: "outline",
  RETURNED: "destructive",
};

const FILTERS: (DeliveryStatus | "ALL")[] = ["ALL", "IN TRANSIT", "DELIVERED", "DELAYED", "RETURNED"];

export default function Dashboard() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const orders = useQuery({
    queryKey: ["orders", filter],
    queryFn: () =>
      api.listOrders(filter === "ALL" ? undefined : { delivery_status: filter }),
  });

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Backend</CardTitle>
          </CardHeader>
          <CardContent>
            {health.data ? (
              <Badge variant={health.data.db === "up" ? "default" : "destructive"}>
                DB {health.data.db}
              </Badge>
            ) : health.isLoading ? (
              <p className="text-sm text-muted-foreground">Checking…</p>
            ) : (
              <Badge variant="destructive">Unreachable</Badge>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Orders shown</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{orders.data?.length ?? "—"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Revenue shown</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {orders.data
                ? formatINR(orders.data.reduce((s, o) => s + o.items.reduce((t, i) => t + i.final_price, 0), 0))
                : "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Orders</CardTitle>
          <div className="flex gap-2">
            {FILTERS.map((f) => (
              <Button
                key={f}
                variant={filter === f ? "default" : "outline"}
                size="sm"
                onClick={() => setFilter(f)}
              >
                {f}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          {orders.isError ? (
            <p className="text-sm text-destructive">
              Could not load orders — is the backend running?
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(orders.data ?? []).map((o) => (
                  <TableRow key={o.order_id}>
                    <TableCell>
                      <Link className="underline" to={`/orders/${o.order_id}`}>
                        #{o.order_id}
                      </Link>
                    </TableCell>
                    <TableCell>{o.customer_id}</TableCell>
                    <TableCell>{o.order_date}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[o.delivery_status]}>
                        {o.delivery_status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {formatINR(o.items.reduce((t, i) => t + i.final_price, 0))}
                    </TableCell>
                  </TableRow>
                ))}
                {orders.data?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <span className="inline-flex items-center gap-2 text-muted-foreground">
                        <PackageSearch size={16} /> No orders match this filter.
                      </span>
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
