/** Order detail — full order view with delivery status transitions. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { ArrowLeft, Lock } from "lucide-react";
import { ApiError, api, formatINRFull, type DeliveryStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_CONFIG: Record<
  DeliveryStatus,
  { dot: string; text: string; bg: string; label: string }
> = {
  "IN TRANSIT": {
    dot: "bg-[#0071e3]", text: "text-[#0071e3]",
    bg: "bg-[#0071e3]/8", label: "In transit",
  },
  DELIVERED: {
    dot: "bg-[#1d8127]", text: "text-[#1d8127]",
    bg: "bg-[#1d8127]/8", label: "Delivered",
  },
  DELAYED: {
    dot: "bg-[#b25e09]", text: "text-[#b25e09]",
    bg: "bg-[#b25e09]/8", label: "Delayed",
  },
  RETURNED: {
    dot: "bg-[#ff3b30]", text: "text-[#ff3b30]",
    bg: "bg-[#ff3b30]/8", label: "Returned",
  },
};

const TRANSITION_OPTIONS: {
  status: DeliveryStatus;
  label: string;
  border: string;
  text: string;
  hover: string;
}[] = [
  {
    status: "DELIVERED",
    label: "Mark as delivered",
    border: "border-[#1d8127]/40",
    text:   "text-[#1d8127]",
    hover:  "hover:bg-[#1d8127]/6",
  },
  {
    status: "DELAYED",
    label: "Mark as delayed",
    border: "border-[#b25e09]/40",
    text:   "text-[#b25e09]",
    hover:  "hover:bg-[#b25e09]/6",
  },
  {
    status: "RETURNED",
    label: "Mark as returned",
    border: "border-[#ff3b30]/40",
    text:   "text-[#ff3b30]",
    hover:  "hover:bg-[#ff3b30]/6",
  },
];

export default function OrderDetail() {
  const { id } = useParams();
  const orderId = Number(id);
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const order = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => api.getOrder(orderId),
  });

  const transition = useMutation({
    mutationFn: (to: DeliveryStatus) => api.transition(orderId, to),
    onSuccess: () => {
      setError(null);
      qc.invalidateQueries({ queryKey: ["order", orderId] });
      qc.invalidateQueries({ queryKey: ["orders"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not update order status. Please try again."),
  });

  if (order.isLoading) {
    return (
      <div className="space-y-4 pt-4">
        {[100, 60, 80].map((w, i) => (
          <div key={i} className="h-4 animate-pulse rounded-full bg-[#f5f5f7]" style={{ width: `${w}%` }} />
        ))}
      </div>
    );
  }

  if (order.isError || !order.data) {
    return (
      <div className="pt-4">
        <p className="text-[15px] text-[#ff3b30]">Order #{id} could not be found.</p>
        <Link to="/orders" className="mt-3 inline-flex items-center gap-1.5 text-[14px] text-[#0071e3] hover:underline">
          <ArrowLeft size={14} /> Back to orders
        </Link>
      </div>
    );
  }

  const o = order.data;
  const total = o.items.reduce((t, i) => t + i.final_price, 0);
  const isTerminal = o.delivery_status !== "IN TRANSIT";
  const cfg = STATUS_CONFIG[o.delivery_status];

  return (
    <div className="space-y-8">

      {/* Breadcrumb */}
      <Link
        to="/orders"
        className="inline-flex items-center gap-1.5 text-[14px] font-medium text-[#0071e3] hover:underline"
      >
        <ArrowLeft size={14} /> All orders
      </Link>

      {/* Order header */}
      <div className="flex items-start justify-between border-b border-[#d2d2d7]/60 pb-6">
        <div className="space-y-1">
          <h1 className="text-[34px] font-semibold tabular-nums tracking-tight text-[#1d1d1f]">
            Order #{o.order_id}
          </h1>
          <p className="text-[15px] text-[#6e6e73]">
            Customer {o.customer_id} · Placed {o.order_date} · Shipping to {o.ship_to_city}
          </p>
          <p className="text-[13px] text-[#aeaeb2]">
            Paid via {o.payment_method} · {o.device} · {o.shipping_time_days}-day delivery
          </p>
        </div>

        <div className="flex flex-col items-end gap-3">
          <span className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[13px] font-semibold", cfg.bg, cfg.text)}>
            <span className={cn("size-1.5 rounded-full", cfg.dot)} />
            {cfg.label}
          </span>
          <p className="text-[28px] font-semibold tabular-nums tracking-tight text-[#1d1d1f]">
            {formatINRFull(total)}
          </p>
        </div>
      </div>

      {/* Line items */}
      <div className="space-y-3">
        <h2 className="text-[17px] font-semibold text-[#1d1d1f]">Items ordered</h2>
        <div className="overflow-hidden rounded-2xl border border-[#d2d2d7]/60 bg-white">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#f5f5f7]">
                {[
                  { label: "Product",  align: "left" },
                  { label: "Seller",   align: "left" },
                  { label: "Qty",      align: "right" },
                  { label: "Price",    align: "right" },
                  { label: "Discount", align: "right" },
                  { label: "Total",    align: "right" },
                ].map(({ label, align }) => (
                  <th
                    key={label}
                    className={`px-5 py-3.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73] text-${align}`}
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {o.items.map((item, idx) => (
                <tr key={item.order_item_id} className={idx > 0 ? "border-t border-[#f5f5f7]" : ""}>
                  <td className="px-5 py-3.5 text-[14px] font-semibold text-[#1d1d1f]">
                    {item.product_id}
                  </td>
                  <td className="px-5 py-3.5 text-[14px] text-[#6e6e73]">{item.seller_id}</td>
                  <td className="px-5 py-3.5 text-right text-[13px] tabular-nums text-[#6e6e73]">
                    {item.quantity}
                  </td>
                  <td className="px-5 py-3.5 text-right text-[13px] tabular-nums text-[#6e6e73]">
                    {formatINRFull(item.unit_price)}
                  </td>
                  <td className="px-5 py-3.5 text-right text-[13px] tabular-nums text-[#6e6e73]">
                    {item.discount_pct > 0 ? `−${item.discount_pct}%` : "—"}
                  </td>
                  <td className="px-5 py-3.5 text-right text-[14px] font-semibold tabular-nums text-[#1d1d1f]">
                    {formatINRFull(item.final_price)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-[#d2d2d7]/60 bg-[#f5f5f7]/50">
                <td
                  colSpan={5}
                  className="px-5 py-3.5 text-right text-[13px] font-semibold uppercase tracking-[0.06em] text-[#6e6e73]"
                >
                  Order total
                </td>
                <td className="px-5 py-3.5 text-right text-[16px] font-semibold tabular-nums text-[#1d1d1f]">
                  {formatINRFull(total)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Status management */}
      <div className="rounded-2xl border border-[#d2d2d7]/60 bg-white p-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[15px] font-semibold text-[#1d1d1f]">Update delivery status</p>
            <p className="mt-0.5 text-[13px] text-[#6e6e73]">
              {isTerminal
                ? "This order has already reached its final state and cannot be changed."
                : "Select a new status to update this order. This action cannot be undone."}
            </p>
          </div>

          {isTerminal ? (
            <div className="flex shrink-0 items-center gap-1.5 rounded-full border border-[#d2d2d7] px-3 py-1.5 text-[13px] text-[#aeaeb2]">
              <Lock size={13} /> Finalised
            </div>
          ) : (
            <div className="flex shrink-0 flex-wrap gap-2">
              {TRANSITION_OPTIONS.map(({ status, label, border, text, hover }) => (
                <button
                  key={status}
                  disabled={transition.isPending}
                  onClick={() => transition.mutate(status)}
                  className={cn(
                    "rounded-full border px-4 py-2 text-[13px] font-semibold transition-colors disabled:opacity-40",
                    border, text, hover
                  )}
                >
                  {transition.isPending ? "Updating…" : label}
                </button>
              ))}
            </div>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-[#ff3b30]/30 bg-[#ff3b30]/5 px-4 py-3 text-[13px] font-medium text-[#ff3b30]">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
