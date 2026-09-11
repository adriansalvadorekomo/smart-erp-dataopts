/** All orders — filterable order list for operations staff. */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { api, formatINR, type DeliveryStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

type Filter = DeliveryStatus | "ALL";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "ALL",        label: "All orders" },
  { key: "IN TRANSIT", label: "In transit" },
  { key: "DELIVERED",  label: "Delivered" },
  { key: "DELAYED",    label: "Delayed" },
  { key: "RETURNED",   label: "Returned" },
];

const STATUS_DOT: Record<DeliveryStatus, string> = {
  "IN TRANSIT": "bg-[#0071e3]",
  DELIVERED:    "bg-[#1d8127]",
  DELAYED:      "bg-[#b25e09]",
  RETURNED:     "bg-[#ff3b30]",
};
const STATUS_TEXT: Record<DeliveryStatus, string> = {
  "IN TRANSIT": "text-[#0071e3]",
  DELIVERED:    "text-[#1d8127]",
  DELAYED:      "text-[#b25e09]",
  RETURNED:     "text-[#ff3b30]",
};
const STATUS_LABEL: Record<DeliveryStatus, string> = {
  "IN TRANSIT": "In transit",
  DELIVERED:    "Delivered",
  DELAYED:      "Delayed",
  RETURNED:     "Returned",
};

export default function Orders() {
  const [filter, setFilter] = useState<Filter>("ALL");

  const orders = useQuery({
    queryKey: ["orders", filter],
    queryFn: () =>
      api.listOrders(
        filter === "ALL"
          ? { limit: 50 }
          : { delivery_status: filter, limit: 50 }
      ),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-8">

      {/* Header */}
      <div className="flex items-end justify-between border-b border-[#d2d2d7]/60 pb-6">
        <div>
          <h1 className="text-[34px] font-semibold tracking-tight text-[#1d1d1f]">Orders</h1>
          <p className="mt-1 text-[15px] text-[#6e6e73]">
            {orders.data
              ? `Showing ${orders.data.length} orders · most recent first`
              : "Loading orders…"}
          </p>
        </div>
        <Link
          to="/new"
          className="rounded-full bg-[#0071e3] px-5 py-2.5 text-[14px] font-semibold text-white transition-opacity hover:opacity-90"
        >
          New order
        </Link>
      </div>

      {/* Status filters */}
      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={cn(
              "rounded-full px-4 py-2 text-[13px] font-medium transition-all",
              filter === key
                ? "bg-[#1d1d1f] text-white"
                : "border border-[#d2d2d7] bg-white text-[#6e6e73] hover:border-[#1d1d1f] hover:text-[#1d1d1f]"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Orders table */}
      <div className="overflow-hidden rounded-2xl border border-[#d2d2d7]/60 bg-white">
        {orders.isError ? (
          <div className="px-6 py-10 text-center">
            <p className="text-[14px] text-[#ff3b30]">
              Could not load orders. Please check the connection and try again.
            </p>
          </div>
        ) : orders.isLoading ? (
          <div className="space-y-0 divide-y divide-[#f5f5f7]">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="flex items-center gap-4 px-5 py-4">
                <div className="h-3 w-16 animate-pulse rounded-full bg-[#f5f5f7]" />
                <div className="h-3 w-24 animate-pulse rounded-full bg-[#f5f5f7]" />
                <div className="h-3 w-20 animate-pulse rounded-full bg-[#f5f5f7]" />
              </div>
            ))}
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#f5f5f7]">
                {[
                  { label: "Order #", align: "left" },
                  { label: "Customer", align: "left" },
                  { label: "Date",     align: "left" },
                  { label: "City",     align: "left" },
                  { label: "Status",   align: "left" },
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
              {(orders.data ?? []).map((o, idx) => {
                const total = o.items.reduce((t, i) => t + i.final_price, 0);
                return (
                  <tr
                    key={o.order_id}
                    className={cn(
                      "transition-colors hover:bg-[#f5f5f7]/60",
                      idx > 0 ? "border-t border-[#f5f5f7]" : ""
                    )}
                  >
                    <td className="px-5 py-3.5">
                      <Link
                        to={`/orders/${o.order_id}`}
                        className="text-[14px] font-semibold tabular-nums text-[#0071e3] hover:underline"
                      >
                        #{o.order_id}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 text-[14px] text-[#6e6e73]">{o.customer_id}</td>
                    <td className="px-5 py-3.5 text-[14px] tabular-nums text-[#6e6e73]">{o.order_date}</td>
                    <td className="px-5 py-3.5 text-[14px] text-[#6e6e73]">{o.ship_to_city}</td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center gap-1.5 text-[13px] font-medium">
                        <span className={cn("size-1.5 shrink-0 rounded-full", STATUS_DOT[o.delivery_status])} />
                        <span className={STATUS_TEXT[o.delivery_status]}>
                          {STATUS_LABEL[o.delivery_status]}
                        </span>
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right text-[14px] font-semibold tabular-nums text-[#1d1d1f]">
                      {formatINR(total)}
                    </td>
                  </tr>
                );
              })}
              {orders.data?.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-14 text-center text-[14px] text-[#6e6e73]">
                    No orders found with this status.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
