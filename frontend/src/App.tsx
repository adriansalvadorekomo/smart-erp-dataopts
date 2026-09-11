/**
 * App shell — navigation reflects how a business user thinks.
 * No technical identifiers in labels. Sections reflect business intent.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  BarChart3, Boxes, LayoutDashboard, Package, Plus, TrendingUp, Users,
} from "lucide-react";
import { Suspense, lazy } from "react";
import {
  Link, NavLink, Route, BrowserRouter as Router, Routes,
} from "react-router-dom";
import { cn } from "@/lib/utils";

const Overview    = lazy(() => import("./pages/Overview"));
const Sales       = lazy(() => import("./pages/Sales"));
const Operations  = lazy(() => import("./pages/Operations"));
const Sellers     = lazy(() => import("./pages/Sellers"));
const Pipeline    = lazy(() => import("./pages/Pipeline"));
const Orders      = lazy(() => import("./pages/Orders"));
const OrderDetail = lazy(() => import("./pages/OrderDetail"));
const CreateOrder = lazy(() => import("./pages/CreateOrder"));

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1 } },
});

function NavSection({ label }: { label: string }) {
  return (
    <p className="mb-1 mt-6 px-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#aeaeb2] first:mt-0">
      {label}
    </p>
  );
}

function NavItem({
  to,
  icon,
  label,
  end,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[14px] transition-colors",
          isActive
            ? "bg-[#e8e8ed] font-semibold text-[#1d1d1f]"
            : "font-normal text-[#6e6e73] hover:bg-[#e8e8ed]/60 hover:text-[#1d1d1f]"
        )
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}

function PageFallback() {
  return (
    <div className="space-y-3 pt-4">
      {[80, 60, 40].map((w, i) => (
        <div
          key={i}
          className="h-3 animate-pulse rounded-full bg-[#f5f5f7]"
          style={{ width: `${w}%` }}
        />
      ))}
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <Router>
        <div className="flex min-h-screen bg-[#f5f5f7]">

          {/* ── Sidebar ───────────────────────────────────────────────────── */}
          <aside className="sticky top-0 hidden h-screen w-[216px] shrink-0 flex-col border-r border-[#d2d2d7]/60 bg-[#fbfbfd] p-4 md:flex">
            <Link
              to="/"
              className="mb-1 flex items-center gap-2 px-1 pb-4 text-[15px] font-semibold tracking-tight text-[#1d1d1f]"
            >
              Smart ERP
            </Link>

            <nav className="flex flex-1 flex-col gap-0.5">
              <NavSection label="Analytics" />
              <NavItem to="/" end icon={<LayoutDashboard size={15} strokeWidth={2} />} label="Overview" />
              <NavItem to="/sales"       icon={<TrendingUp  size={15} strokeWidth={2} />} label="Sales" />
              <NavItem to="/operations"  icon={<BarChart3   size={15} strokeWidth={2} />} label="Operations" />
              <NavItem to="/sellers"     icon={<Users       size={15} strokeWidth={2} />} label="Sellers" />

              <NavSection label="Platform" />
              <NavItem to="/pipeline"    icon={<Boxes       size={15} strokeWidth={2} />} label="Data Platform" />

              <NavSection label="Orders" />
              <NavItem to="/orders"      icon={<Package     size={15} strokeWidth={2} />} label="All orders" />
              <NavItem to="/new"         icon={<Plus        size={15} strokeWidth={2} />} label="New order" />
            </nav>

            <div className="border-t border-[#d2d2d7]/50 pt-4">
              <p className="px-1 text-[11px] leading-relaxed text-[#aeaeb2]">
                India marketplace<br />
                24-month dataset
              </p>
            </div>
          </aside>

          {/* ── Main ──────────────────────────────────────────────────────── */}
          <div className="min-w-0 flex-1">

            {/* Mobile top nav */}
            <div className="flex gap-0 overflow-x-auto border-b border-[#d2d2d7]/60 bg-[#fbfbfd] px-3 md:hidden">
              {[
                { to: "/",           label: "Overview", end: true },
                { to: "/sales",      label: "Sales" },
                { to: "/operations", label: "Operations" },
                { to: "/sellers",    label: "Sellers" },
                { to: "/pipeline",   label: "Platform" },
                { to: "/orders",     label: "Orders" },
              ].map(({ to, label, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      "shrink-0 border-b-2 px-4 py-3 text-[13px] font-medium transition-colors",
                      isActive
                        ? "border-[#0071e3] text-[#0071e3]"
                        : "border-transparent text-[#6e6e73]"
                    )
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>

            <div className="mx-auto max-w-5xl px-6 py-10">
              <Suspense fallback={<PageFallback />}>
                <Routes>
                  <Route path="/"            element={<Overview />} />
                  <Route path="/sales"       element={<Sales />} />
                  <Route path="/operations"  element={<Operations />} />
                  <Route path="/sellers"     element={<Sellers />} />
                  <Route path="/pipeline"    element={<Pipeline />} />
                  <Route path="/orders"      element={<Orders />} />
                  <Route path="/orders/:id"  element={<OrderDetail />} />
                  <Route path="/new"         element={<CreateOrder />} />
                </Routes>
              </Suspense>
            </div>
          </div>

        </div>
      </Router>
    </QueryClientProvider>
  );
}
