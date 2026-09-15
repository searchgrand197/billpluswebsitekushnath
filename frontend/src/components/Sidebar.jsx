import React, { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  ShoppingCart,
  FileText,
  Users,
  Package,
  Boxes,
  Truck,
  CreditCard,
  BarChart3,
  Scale,
  Settings,
  Leaf,
  Factory,
  ChevronDown,
} from 'lucide-react';

export default function Sidebar() {
  const [isHovered, setIsHovered] = useState(false);
  const location = useLocation();
  const purchaseActive = location.pathname.startsWith('/purchase') || location.pathname.startsWith('/suppliers');
  const [purchaseOpen, setPurchaseOpen] = useState(purchaseActive);

  useEffect(() => {
    if (purchaseActive) setPurchaseOpen(true);
  }, [purchaseActive]);

  return (
    <aside
      className={`sidebar ${isHovered ? 'expanded' : 'collapsed'}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="brand-header">
        <div className="brand-icon-box">
          <Leaf size={24} color="#0F766E" />
        </div>
        <div className="brand-text">
          <div className="brand-name">Billvice</div>
          <div className="brand-subtext">AYURVEDIC ERP</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Dashboard">
          <LayoutDashboard size={20} className="nav-icon" />
          <span className="nav-label">Dashboard</span>
        </NavLink>

        <NavLink to="/pos" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Billing">
          <ShoppingCart size={20} className="nav-icon" />
          <span className="nav-label">Billing</span>
        </NavLink>

        <NavLink to="/raw-materials" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Raw Materials">
          <Leaf size={20} className="nav-icon" />
          <span className="nav-label">Raw Materials</span>
        </NavLink>

        <NavLink to="/manufacturing" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Manufacturing Unit">
          <Factory size={20} className="nav-icon" />
          <span className="nav-label">Manufacturing</span>
        </NavLink>

        <NavLink to="/products" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Products Catalog">
          <Package size={20} className="nav-icon" />
          <span className="nav-label">Finished Products</span>
        </NavLink>

        <NavLink to="/stock" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Stock Monitor">
          <Boxes size={20} className="nav-icon" />
          <span className="nav-label">Stock Monitor</span>
        </NavLink>

        <NavLink to="/customers" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Customers & Ledger">
          <Users size={20} className="nav-icon" />
          <span className="nav-label">Customers & Ledger</span>
        </NavLink>

        <button
          type="button"
          className={`nav-item nav-drop-btn ${purchaseActive ? 'active' : ''}`}
          title="Purchase"
          onClick={() => setPurchaseOpen((open) => !open)}
        >
          <Truck size={20} className="nav-icon" />
          <span className="nav-label">Purchase</span>
          <ChevronDown size={16} className={`nav-chevron ${purchaseOpen ? 'open' : ''}`} />
        </button>
        {purchaseOpen && (
          <div className="nav-submenu">
            <NavLink to="/purchase-orders" end className={({ isActive }) => `nav-item nav-subitem ${isActive ? 'active' : ''}`}>Purchase Orders</NavLink>
            <NavLink to="/purchase-orders/create" className={({ isActive }) => `nav-item nav-subitem ${isActive ? 'active' : ''}`}>Create PO</NavLink>
            <NavLink to="/purchase-inward" className={({ isActive }) => `nav-item nav-subitem ${isActive ? 'active' : ''}`}>Inward / Received</NavLink>
            <NavLink to="/purchase-orders" end className={({ isActive }) => `nav-item nav-subitem ${isActive ? 'active' : ''}`}>Purchase History</NavLink>
            <NavLink to="/suppliers" className={({ isActive }) => `nav-item nav-subitem ${isActive ? 'active' : ''}`}>Suppliers</NavLink>
          </div>
        )}

        <NavLink to="/dues" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Dues & Collections">
          <CreditCard size={20} className="nav-icon" />
          <span className="nav-label">Dues & Collections</span>
        </NavLink>

        <NavLink to="/invoices" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Sales History">
          <FileText size={20} className="nav-icon" />
          <span className="nav-label">Sales History</span>
        </NavLink>



        <NavLink to="/reports" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="ERP Reports">
          <BarChart3 size={20} className="nav-icon" />
          <span className="nav-label">ERP Reports</span>
        </NavLink>

        <NavLink to="/balance-sheet" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Balance Sheet">
          <Scale size={20} className="nav-icon" />
          <span className="nav-label">Balance Sheet</span>
        </NavLink>

        <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} title="Settings">
          <Settings size={20} className="nav-icon" />
          <span className="nav-label">Settings</span>
        </NavLink>
      </nav>
    </aside>
  );
}
