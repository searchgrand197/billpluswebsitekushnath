import React from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import { AuthProvider, useAuth } from './components/AuthContext';
import { ToastProvider } from './components/ToastContext';
import { setUnauthorizedHandler } from './api';
import { attachClearZeroOnType } from './clearZeroOnType';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import PosBilling from './pages/PosBilling';
import Invoices from './pages/Invoices';
import Customers from './pages/Customers';
import Products from './pages/Products';
import Stock from './pages/Stock';
import PurchaseOrders from './pages/PurchaseOrders';
import PurchaseOrderForm from './pages/PurchaseOrderForm';
import PurchaseOrderDetail from './pages/PurchaseOrderDetail';
import PurchaseInward from './pages/PurchaseInward';
import Suppliers from './pages/Suppliers';
import DuesCollections from './pages/DuesCollections';
import Reports from './pages/Reports';
import BalanceSheet from './pages/BalanceSheet';
import Settings from './pages/Settings';
import RawMaterials from './pages/RawMaterials';
import Manufacturing from './pages/Manufacturing';

function ProtectedLayout() {
  const { user, ready, clearSession } = useAuth();
  const location = useLocation();

  React.useEffect(() => {
    // Soft clear only — hard logout API on a dead session caused blank/flicker on production
    setUnauthorizedHandler(() => clearSession());
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  if (!ready) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748B', fontWeight: 700 }}>
        Loading…
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-content">
        <Navbar />
        <main className="page-body">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/pos" element={<PosBilling />} />
            <Route path="/raw-materials" element={<RawMaterials />} />
            <Route path="/manufacturing" element={<Manufacturing />} />
            <Route path="/invoices" element={<Invoices />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/products" element={<Products />} />
            <Route path="/stock" element={<Stock />} />
            <Route path="/purchase-orders" element={<PurchaseOrders />} />
            <Route path="/purchase-orders/create" element={<PurchaseOrderForm />} />
            <Route path="/purchase-orders/:id/edit" element={<PurchaseOrderForm />} />
            <Route path="/purchase-orders/:id" element={<PurchaseOrderDetail />} />
            <Route path="/purchase-inward" element={<PurchaseInward />} />
            <Route path="/suppliers" element={<Suppliers />} />
            <Route path="/dues" element={<DuesCollections />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/balance-sheet" element={<BalanceSheet />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  React.useEffect(() => attachClearZeroOnType(), []);

  return (
    <AuthProvider>
      <ToastProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </ToastProvider>
    </AuthProvider>
  );
}
