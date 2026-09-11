/** Typed client for the Smart-ERP backend (mirrors backend/app/schemas/orders.py).
 * Base '/api' hits the Vite dev proxy (same-origin); set VITE_API_URL for
 * separate deploys (backend CORS allows the frontend origin).
 */
const BASE = import.meta.env.VITE_API_URL ?? "/api";

export type DeliveryStatus = "IN TRANSIT" | "DELIVERED" | "DELAYED" | "RETURNED";

export interface OrderItem {
  order_item_id: number;
  order_id: number;
  product_id: string;
  seller_id: string;
  quantity: number;
  unit_price: number;
  discount_pct: number;
  final_price: number;
  seller_rating_at_sale: number;
}

export interface Order {
  order_id: number;
  customer_id: string;
  order_date: string;
  ship_to_city: string;
  payment_method: string;
  device: string;
  delivery_status: DeliveryStatus;
  shipping_time_days: number;
  items: OrderItem[];
}

export interface OrderItemCreate {
  product_id: string;
  seller_id: string;
  quantity: number;
  unit_price: number;
  discount_pct: number;
}

export interface OrderCreate {
  customer_id: string;
  order_date: string;
  ship_to_city: string;
  payment_method: string;
  device: string;
  shipping_time_days: number;
  items: OrderItemCreate[];
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body?.detail === "string" ? body.detail : `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

export const api = {
  health: () => request<{ status: string; db: string }>("/health"),
  listOrders: (params?: { customer_id?: string; delivery_status?: DeliveryStatus }) => {
    const q = new URLSearchParams();
    if (params?.customer_id) q.set("customer_id", params.customer_id);
    if (params?.delivery_status) q.set("delivery_status", params.delivery_status);
    const suffix = q.size > 0 ? `?${q}` : "";
    return request<Order[]>(`/orders${suffix}`);
  },
  getOrder: (id: number) => request<Order>(`/orders/${id}`),
  createOrder: (payload: OrderCreate) =>
    request<Order>("/orders", { method: "POST", body: JSON.stringify(payload) }),
  transition: (id: number, delivery_status: DeliveryStatus) =>
    request<Order>(`/orders/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ delivery_status }),
    }),
};

export function formatINR(n: number): string {
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
