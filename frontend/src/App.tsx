import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LayoutDashboard, Plus } from "lucide-react";
import { Link, NavLink, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { cn } from "@/lib/utils";
import CreateOrder from "./pages/CreateOrder";
import Dashboard from "./pages/Dashboard";
import OrderDetail from "./pages/OrderDetail";

const qc = new QueryClient();

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
          <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col gap-6 border-r border-border/60 bg-sidebar p-5 md:flex">
            <Link to="/" className="px-1 text-[17px] font-semibold tracking-tight">
              Smart-ERP
            </Link>
            <nav className="flex flex-col gap-1">
              <NavItem to="/" end icon={<LayoutDashboard size={18} strokeWidth={1.75} />} label="Orders" />
              <NavItem to="/new" icon={<Plus size={18} strokeWidth={1.75} />} label="New order" />
            </nav>
            <p className="mt-auto px-1 text-xs text-muted-foreground">Ops console · Phase 5</p>
          </aside>
          <div className="min-w-0 flex-1">
            <div className="mx-auto max-w-4xl space-y-8 px-6 py-10">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/orders/:id" element={<OrderDetail />} />
                <Route path="/new" element={<CreateOrder />} />
              </Routes>
            </div>
          </div>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
