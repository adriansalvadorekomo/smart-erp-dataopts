import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Boxes, LayoutDashboard, Plus, Rows3 } from "lucide-react";
import { Suspense, lazy } from "react";
import { Link, NavLink, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { cn } from "@/lib/utils";

const Overview = lazy(() => import("./pages/Overview"));
const Pipeline = lazy(() => import("./pages/Pipeline"));
const Orders = lazy(() => import("./pages/Orders"));
const OrderDetail = lazy(() => import("./pages/OrderDetail"));
const CreateOrder = lazy(() => import("./pages/CreateOrder"));

const qc = new QueryClient();

function Section({ label }: { label: string }) {
  return <p className="px-3 pt-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>;
}

function NavItem({ to, icon, label, end }: { to: string; icon: React.ReactNode; label: string; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-xl px-3 py-2 text-[15px] transition-colors",
          isActive
            ? "bg-secondary font-semibold text-foreground"
            : "font-normal text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
        )
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}

function App() {
  return (
    <QueryClientProvider client={qc}>
      <Router>
        <div className="flex min-h-screen">
          <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col bg-sidebar p-5 md:flex border-r border-border/60">
            <Link to="/" className="px-1 text-[17px] font-semibold tracking-tight">
              Smart-ERP
            </Link>
            <nav className="flex flex-col gap-0.5">
              <Section label="Analyze" />
              <NavItem to="/" end icon={<LayoutDashboard size={18} strokeWidth={1.75} />} label="Overview" />
              <NavItem to="/pipeline" icon={<Boxes size={18} strokeWidth={1.75} />} label="Pipeline" />
              <Section label="Operate" />
              <NavItem to="/orders" icon={<Rows3 size={18} strokeWidth={1.75} />} label="Orders" />
              <NavItem to="/new" icon={<Plus size={18} strokeWidth={1.75} />} label="New order" />
            </nav>
          </aside>
          <div className="min-w-0 flex-1">
            <div className="mx-auto max-w-5xl space-y-8 px-6 py-10">
              <nav className="flex gap-5 border-b border-border/60 pb-3 text-[15px] md:hidden">
                <NavLink to="/" end className={({ isActive }) => (isActive ? "font-semibold" : "text-muted-foreground")}>
                  Overview
                </NavLink>
                <NavLink to="/pipeline" className={({ isActive }) => (isActive ? "font-semibold" : "text-muted-foreground")}>
                  Pipeline
                </NavLink>
                <NavLink to="/orders" className={({ isActive }) => (isActive ? "font-semibold" : "text-muted-foreground")}>
                  Orders
                </NavLink>
                <NavLink to="/new" className={({ isActive }) => (isActive ? "font-semibold" : "text-muted-foreground")}>
                  New
                </NavLink>
              </nav>
              <Suspense fallback={<p className="text-[15px] text-muted-foreground">Loading…</p>}>
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/pipeline" element={<Pipeline />} />
                <Route path="/orders" element={<Orders />} />
                <Route path="/orders/:id" element={<OrderDetail />} />
                <Route path="/new" element={<CreateOrder />} />
              </Routes>
              </Suspense>
            </div>
          </div>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
