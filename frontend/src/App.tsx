import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Link, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import CreateOrder from "./pages/CreateOrder";
import Dashboard from "./pages/Dashboard";
import OrderDetail from "./pages/OrderDetail";

const qc = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={qc}>
      <Router>
        <div className="mx-auto min-h-screen max-w-5xl space-y-6 p-6">
          <header className="flex items-center justify-between">
            <Link to="/" className="text-xl font-bold">
              Smart-ERP · Ops
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link className="underline" to="/">
                Orders
              </Link>
              <Link className="underline" to="/new">
                New order
              </Link>
            </nav>
          </header>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/orders/:id" element={<OrderDetail />} />
            <Route path="/new" element={<CreateOrder />} />
          </Routes>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
