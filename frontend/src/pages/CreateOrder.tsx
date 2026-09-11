import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError, api, type OrderItemCreate } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const EMPTY_LINE: OrderItemCreate = {
  product_id: "",
  seller_id: "",
  quantity: 1,
  unit_price: 0,
  discount_pct: 0,
};

export default function CreateOrder() {
  const nav = useNavigate();
  const [customerId, setCustomerId] = useState("");
  const [city, setCity] = useState("");
  const [lines, setLines] = useState<OrderItemCreate[]>([{ ...EMPTY_LINE }]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function setLine(i: number, patch: Partial<OrderItemCreate>) {
    setLines((ls) => ls.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const order = await api.createOrder({
        customer_id: customerId.trim(),
        order_date: new Date().toISOString().slice(0, 10),
        ship_to_city: city.trim(),
        payment_method: "UPI",
        device: "Web",
        shipping_time_days: 2,
        items: lines.map((l) => ({
          ...l,
          product_id: l.product_id.trim(),
          seller_id: l.seller_id.trim(),
          quantity: Number(l.quantity),
          unit_price: Number(l.unit_price),
          discount_pct: Number(l.discount_pct),
        })),
      });
      nav(`/orders/${order.order_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Link to="/orders" className="inline-flex items-center gap-1 text-[15px] text-primary hover:underline">
        <ArrowLeft size={16} /> Orders
      </Link>
      <div>
        <h1 className="text-[32px] font-semibold tracking-tight">New order</h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Totals are computed server-side — the API never trusts client money.
        </p>
      </div>

      <Card className="border-border/60 shadow-sm">
        <CardContent className="pt-6">
          <form onSubmit={submit} className="space-y-5">
            <div className="grid gap-3 md:grid-cols-2">
              <Input
                placeholder="Customer ID"
                aria-label="Customer ID"
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                required
              />
              <Input
                placeholder="Ship-to city"
                aria-label="Ship-to city"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <p className="text-[13px] font-medium text-muted-foreground">Lines</p>
              {lines.map((l, i) => (
                <div key={i} className="grid gap-2 md:grid-cols-5">
                  <Input placeholder="Product" aria-label="Product" value={l.product_id} onChange={(e) => setLine(i, { product_id: e.target.value })} required />
                  <Input placeholder="Seller" aria-label="Seller" value={l.seller_id} onChange={(e) => setLine(i, { seller_id: e.target.value })} required />
                  <Input type="number" min={1} placeholder="Qty" aria-label="Quantity" value={l.quantity} onChange={(e) => setLine(i, { quantity: Number(e.target.value) })} required />
                  <Input type="number" min={0} step="0.01" placeholder="Unit ₹" aria-label="Unit price" value={l.unit_price} onChange={(e) => setLine(i, { unit_price: Number(e.target.value) })} required />
                  <Input type="number" min={0} max={70} step="0.01" placeholder="Disc %" aria-label="Discount percent" value={l.discount_pct} onChange={(e) => setLine(i, { discount_pct: Number(e.target.value) })} />
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" className="rounded-full" onClick={() => setLines((ls) => [...ls, { ...EMPTY_LINE }])}>
                Add line
              </Button>
              <Button type="submit" className="rounded-full" disabled={busy}>
                {busy ? "Creating…" : "Create order"}
              </Button>
            </div>
            {error && <p className="text-[15px] text-destructive">{error}</p>}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
