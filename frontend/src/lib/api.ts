/** Typed client for the Smart-ERP backend.
 * Every method maps to a named business question — see backend/app/api/stats.py.
 * Base '/api' hits the Vite dev proxy (same-origin);
 * set VITE_API_URL for separate deploys.
 */
const BASE = import.meta.env.VITE_API_URL ?? "/api";

// ─── Order types ─────────────────────────────────────────────────────────────

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

// ─── Stats types ──────────────────────────────────────────────────────────────

export interface Overview {
  total_orders: number;
  revenue: number;
  aov: number;
  avg_discount_pct: number;
  return_rate: number;
  delayed_rate: number;
  in_transit: number;
  stock_critical: number;
  by_status: Record<string, number>;
}

export interface TrendPoint {
  date: string;
  orders: number;
  revenue: number;
}

export interface CategoryShare {
  category: string;
  revenue: number;
  lines: number;
}

export interface CategoryTrendPoint {
  month: string;
  category: string;
  revenue: number;
  orders: number;
}

export interface CityPerformance {
  city: string;
  orders: number;
  revenue: number;
  aov: number;
  return_rate: number;
  delayed_rate: number;
}

export interface ChannelRow {
  method?: string;
  device?: string;
  orders: number;
  revenue: number;
  return_rate: number;
}

export interface ChannelMix {
  payment: ChannelRow[];
  device: ChannelRow[];
}

export interface DiscountBand {
  band: string;
  lines: number;
  revenue: number;
}

export interface SellerPerformance {
  seller_id: string;
  orders: number;
  revenue: number;
  avg_rating: number;
  return_rate: number;
  delayed_rate: number;
}

export interface TopSeller {
  seller_id: string;
  revenue: number;
  lines: number;
  avg_rating: number;
}

export interface OpsRow {
  orders: number;
  return_rate: number;
  delayed_rate: number;
  category?: string;
  city?: string;
  payment_method?: string;
  shipping_time_days?: number;
}

export interface OperationsBreakdown {
  by_category: OpsRow[];
  by_city: OpsRow[];
  by_shipping_days: OpsRow[];
  by_payment: OpsRow[];
}

export interface DQCheck {
  rule: string;
  violations: number;
}

// ─── Error class ─────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// ─── Request helper ───────────────────────────────────────────────────────────

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

// ─── API surface ──────────────────────────────────────────────────────────────

export const api = {
  // Health
  health: () => request<{ status: string; db: string }>("/health"),

  // Orders (operational)
  listOrders: (params?: { customer_id?: string; delivery_status?: DeliveryStatus; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.customer_id) q.set("customer_id", params.customer_id);
    if (params?.delivery_status) q.set("delivery_status", params.delivery_status);
    if (params?.limit) q.set("limit", String(params.limit));
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

  // Platform health
  overview: () => request<Overview>("/stats/overview"),
  dqChecks: () => request<DQCheck[]>("/stats/dq-checks"),

  // Sales & revenue
  trend: (days = 90) => request<TrendPoint[]>(`/stats/revenue-trend?days=${days}`),
  categories: () => request<CategoryShare[]>("/stats/revenue-by-category"),
  categoryTrend: () => request<CategoryTrendPoint[]>("/stats/category-trend"),
  salesByCity: () => request<CityPerformance[]>("/stats/sales-by-city"),
  channelMix: () => request<ChannelMix>("/stats/channel-mix"),
  discountBands: () => request<DiscountBand[]>("/stats/discount-bands"),
  pareto: () => request<{ top20_share: number }>("/stats/pareto"),

  // Sellers
  topSellers: (limit = 8) => request<TopSeller[]>(`/stats/top-sellers?limit=${limit}`),
  sellerPerformance: (limit = 50) =>
    request<SellerPerformance[]>(`/stats/seller-performance?limit=${limit}`),

  // Operations
  operationsBreakdown: () => request<OperationsBreakdown>("/stats/operations-breakdown"),
};

// ─── Formatters ───────────────────────────────────────────────────────────────

export function formatINR(n: number, digits = 2): string {
  if (n >= 1e9) return `₹${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(1)}Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(1)}L`;
  return `₹${n.toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

export function formatINRFull(n: number): string {
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export function formatPercent(ratio: number, digits = 1): string {
  return `${(ratio * 100).toFixed(digits)}%`;
}
