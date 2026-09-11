/** New order form — clean, guided, with live price estimate. */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { ApiError, api, type OrderItemCreate } from "@/lib/api";
import { cn } from "@/lib/utils";

const CITIES   = ["Delhi", "Bangalore", "Mumbai", "Chennai", "Hyderabad"];
const PAYMENTS = ["UPI", "Credit Card", "Debit Card", "Cash on Delivery"];
const DEVICES  = ["Mobile App", "Web", "Tablet"];

const EMPTY_LINE: OrderItemCreate = {
  product_id:   "",
  seller_id:    "",
  quantity:     1,
  unit_price:   0,
  discount_pct: 0,
};

// ─── Input primitives ─────────────────────────────────────────────────────────

const inputClass =
  "w-full rounded-xl border border-[#d2d2d7] bg-white px-3.5 py-2.5 text-[14px] text-[#1d1d1f] placeholder:text-[#aeaeb2] focus:border-[#0071e3] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/20 transition-colors";

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-1.5 text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
      {children}
    </p>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
  required,
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  "aria-label"?: string;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      required={required}
      aria-label={ariaLabel}
      className={inputClass}
    />
  );
}

function NumberInput({
  value,
  onChange,
  min = 0,
  max,
  step = "1",
  placeholder,
  "aria-label": ariaLabel,
  required,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: string;
  placeholder?: string;
  "aria-label"?: string;
  required?: boolean;
}) {
  return (
    <input
      type="number"
      value={value || ""}
      onChange={e => onChange(Number(e.target.value))}
      min={min}
      max={max}
      step={step}
      placeholder={placeholder}
      aria-label={ariaLabel}
      required={required}
      className={cn(inputClass, "tabular-nums")}
    />
  );
}

function SelectInput({
  value,
  onChange,
  options,
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  "aria-label"?: string;
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      aria-label={ariaLabel}
      className={cn(inputClass, "appearance-none cursor-pointer")}
    >
      {options.map(o => <option key={o}>{o}</option>)}
    </select>
  );
}

// ─── Price preview ────────────────────────────────────────────────────────────

function lineEstimate(l: OrderItemCreate): number {
  if (!l.unit_price || !l.quantity) return 0;
  return +(l.unit_price * l.quantity * (1 - l.discount_pct / 100)).toFixed(2);
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CreateOrder() {
  const nav = useNavigate();

  const [customerId,    setCustomerId]    = useState("");
  const [city,          setCity]          = useState(CITIES[0]);
  const [payment,       setPayment]       = useState(PAYMENTS[0]);
  const [device,        setDevice]        = useState(DEVICES[1]);
  const [shippingDays,  setShippingDays]  = useState(2);
  const [lines,         setLines]         = useState<OrderItemCreate[]>([{ ...EMPTY_LINE }]);
  const [error,         setError]         = useState<string | null>(null);
  const [busy,          setBusy]          = useState(false);

  function setLine(i: number, patch: Partial<OrderItemCreate>) {
    setLines(ls => ls.map((l, j) => j === i ? { ...l, ...patch } : l));
  }

  function removeLine(i: number) {
    if (lines.length <= 1) return;
    setLines(ls => ls.filter((_, j) => j !== i));
  }

  const estimatedTotal = lines.reduce((s, l) => s + lineEstimate(l), 0);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const order = await api.createOrder({
        customer_id:        customerId.trim(),
        order_date:         new Date().toISOString().slice(0, 10),
        ship_to_city:       city,
        payment_method:     payment,
        device,
        shipping_time_days: shippingDays,
        items: lines.map(l => ({
          ...l,
          product_id:   l.product_id.trim(),
          seller_id:    l.seller_id.trim(),
          quantity:     Number(l.quantity),
          unit_price:   Number(l.unit_price),
          discount_pct: Number(l.discount_pct),
        })),
      });
      nav(`/orders/${order.order_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "The order could not be created. Please check the details and try again."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">

      {/* Header */}
      <div>
        <Link
          to="/orders"
          className="inline-flex items-center gap-1.5 text-[14px] font-medium text-[#0071e3] hover:underline"
        >
          <ArrowLeft size={14} /> All orders
        </Link>
        <div className="mt-4 border-b border-[#d2d2d7]/60 pb-6">
          <h1 className="text-[34px] font-semibold tracking-tight text-[#1d1d1f]">New order</h1>
          <p className="mt-1 text-[15px] text-[#6e6e73]">
            Fill in the order details below. The final price is calculated automatically.
          </p>
        </div>
      </div>

      <form onSubmit={submit} className="space-y-6">

        {/* Order details */}
        <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-6">
          <h2 className="mb-5 text-[16px] font-semibold text-[#1d1d1f]">Order details</h2>
          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <FieldLabel>Customer ID</FieldLabel>
              <TextInput
                value={customerId}
                onChange={setCustomerId}
                placeholder="e.g. U820959"
                required
                aria-label="Customer ID"
              />
            </div>
            <div>
              <FieldLabel>Delivery city</FieldLabel>
              <SelectInput value={city} onChange={setCity} options={CITIES} aria-label="Delivery city" />
            </div>
            <div>
              <FieldLabel>Payment method</FieldLabel>
              <SelectInput value={payment} onChange={setPayment} options={PAYMENTS} aria-label="Payment method" />
            </div>
            <div>
              <FieldLabel>Placed via</FieldLabel>
              <SelectInput value={device} onChange={setDevice} options={DEVICES} aria-label="Device" />
            </div>
            <div>
              <FieldLabel>Estimated delivery (days)</FieldLabel>
              <NumberInput
                value={shippingDays}
                onChange={setShippingDays}
                min={1}
                max={6}
                aria-label="Delivery days"
              />
            </div>
          </div>
        </div>

        {/* Items */}
        <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-6">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-[16px] font-semibold text-[#1d1d1f]">
              Items{" "}
              <span className="text-[14px] font-normal text-[#6e6e73]">({lines.length})</span>
            </h2>
            <button
              type="button"
              onClick={() => setLines(ls => [...ls, { ...EMPTY_LINE }])}
              className="inline-flex items-center gap-1.5 rounded-full border border-[#d2d2d7] px-4 py-1.5 text-[13px] font-medium text-[#1d1d1f] transition-colors hover:bg-[#f5f5f7]"
            >
              <Plus size={13} strokeWidth={2.5} /> Add item
            </button>
          </div>

          <div className="space-y-3">
            {lines.map((l, i) => {
              const est = lineEstimate(l);
              return (
                <div key={i} className="rounded-xl bg-[#f5f5f7]/60 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
                      Item {i + 1}
                    </p>
                    <div className="flex items-center gap-3">
                      {est > 0 && (
                        <span className="text-[13px] font-semibold tabular-nums text-[#1d1d1f]">
                          ≈ ₹{est.toLocaleString("en-IN")}
                        </span>
                      )}
                      {lines.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeLine(i)}
                          aria-label="Remove item"
                          className="text-[#6e6e73] transition-colors hover:text-[#ff3b30]"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-5">
                    <div className="md:col-span-2">
                      <FieldLabel>Product ID</FieldLabel>
                      <TextInput
                        value={l.product_id}
                        onChange={v => setLine(i, { product_id: v })}
                        placeholder="e.g. P39256"
                        required
                        aria-label="Product ID"
                      />
                    </div>
                    <div>
                      <FieldLabel>Seller ID</FieldLabel>
                      <TextInput
                        value={l.seller_id}
                        onChange={v => setLine(i, { seller_id: v })}
                        placeholder="e.g. S1000"
                        required
                        aria-label="Seller ID"
                      />
                    </div>
                    <div>
                      <FieldLabel>Quantity</FieldLabel>
                      <NumberInput
                        value={l.quantity}
                        onChange={v => setLine(i, { quantity: v })}
                        min={1}
                        required
                        aria-label="Quantity"
                      />
                    </div>
                    <div>
                      <FieldLabel>Unit price (₹)</FieldLabel>
                      <NumberInput
                        value={l.unit_price}
                        onChange={v => setLine(i, { unit_price: v })}
                        min={0}
                        step="0.01"
                        required
                        aria-label="Unit price"
                      />
                    </div>
                    <div className="md:col-start-5">
                      <FieldLabel>Discount (%)</FieldLabel>
                      <NumberInput
                        value={l.discount_pct}
                        onChange={v => setLine(i, { discount_pct: v })}
                        min={0}
                        max={70}
                        step="0.01"
                        placeholder="0"
                        aria-label="Discount percent"
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {estimatedTotal > 0 && (
            <div className="mt-5 flex justify-end border-t border-[#d2d2d7]/60 pt-4">
              <div className="text-right">
                <p className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]">
                  Estimated total
                </p>
                <p className="mt-1 text-[24px] font-semibold tabular-nums text-[#1d1d1f]">
                  ₹{estimatedTotal.toLocaleString("en-IN")}
                </p>
                <p className="mt-0.5 text-[11px] text-[#aeaeb2]">
                  Final price confirmed by the server on submission
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-[#ff3b30]/30 bg-[#ff3b30]/5 px-4 py-3 text-[13px] font-medium text-[#ff3b30]">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <Link
            to="/orders"
            className="rounded-full border border-[#d2d2d7] px-5 py-2.5 text-[14px] font-medium text-[#1d1d1f] transition-colors hover:bg-[#f5f5f7]"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={busy}
            className="rounded-full bg-[#0071e3] px-6 py-2.5 text-[14px] font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {busy ? "Creating order…" : "Create order"}
          </button>
        </div>
      </form>
    </div>
  );
}
