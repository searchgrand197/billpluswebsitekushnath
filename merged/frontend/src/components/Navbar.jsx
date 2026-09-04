import React, { useState, useEffect, useRef } from 'react';
import { Search, PlusCircle, FileText, Users, Package, ShoppingBag, X, Loader2, Command, LogOut } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { globalSearch } from '../api';
import { useAuth } from './AuthContext';

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState({ products: [], customers: [], invoices: [] });
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  // Keyboard shortcut listener for Ctrl+K or /
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        setIsOpen(true);
      } else if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Focus input on modal open
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current.focus(), 50);
    }
  }, [isOpen]);

  // Debounced Search API call
  useEffect(() => {
    if (!query.trim()) {
      setResults({ products: [], customers: [], invoices: [] });
      setLoading(false);
      return;
    }

    setLoading(true);
    const timer = setTimeout(() => {
      globalSearch(query)
        .then((res) => {
          setResults(res.data);
          setLoading(false);
          setSelectedIndex(0);
        })
        .catch((err) => {
          console.error(err);
          setLoading(false);
        });
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  // Flatten results for keyboard navigation
  const allFlattenedItems = [
    ...(results.invoices || []).map((item) => ({ ...item, _type: 'invoice', path: '/invoices' })),
    ...(results.customers || []).map((item) => ({ ...item, _type: 'customer', path: '/customers' })),
    ...(results.products || []).map((item) => ({ ...item, _type: 'product', path: '/products' })),
  ];

  const handleKeyDownModal = (e) => {
    if (allFlattenedItems.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % allFlattenedItems.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + allFlattenedItems.length) % allFlattenedItems.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const selected = allFlattenedItems[selectedIndex];
      if (selected) {
        handleSelectItem(selected);
      }
    }
  };

  const handleSelectItem = (item) => {
    setIsOpen(false);
    setQuery('');
    navigate(item.path);
  };

  const totalResultsCount =
    (results.invoices?.length || 0) +
    (results.customers?.length || 0) +
    (results.products?.length || 0);

  return (
    <header className="top-navbar">
      {/* Top Bar Trigger Input */}
      <div style={{ flex: 1, maxWidth: '480px' }}>
        <button
          onClick={() => setIsOpen(true)}
          type="button"
          style={{
            display: 'flex',
            alignItems: 'center',
            justify: 'space-between',
            width: '100%',
            height: '38px',
            padding: '0 12px',
            backgroundColor: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            color: '#64748B',
            fontSize: '0.875rem',
            cursor: 'pointer',
            textAlign: 'left',
            transition: 'all 0.15s ease',
          }}
          className="search-bar-trigger"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Search size={16} color="#94A3B8" />
            <span>Search bills, customers, SKUs...</span>
          </div>
          <span className="search-shortcut-pill">
            <Command size={11} /> K
          </span>
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <Link to="/pos" className="btn-smart btn-primary-smart" style={{ textDecoration: 'none' }}>
          <PlusCircle size={18} />
          New Bill
        </Link>

        <div style={{ width: '1px', height: '24px', backgroundColor: '#E2E8F0' }}></div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: '#CCFBF1', color: '#0F766E', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '700' }}>
            {(user?.username || 'B').slice(0, 1).toUpperCase()}
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#0F172A' }}>{user?.username || 'User'}</div>
            <div style={{ fontSize: '0.75rem', color: '#64748B' }}>Billvice</div>
          </div>
          <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '6px 10px' }} onClick={() => logout()} title="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </div>

      {/* Spotlight Command Palette Modal */}
      {isOpen && (
        <div className="search-modal-overlay" onClick={() => setIsOpen(false)}>
          <div className="search-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="search-modal-header">
              <Search size={20} className="search-modal-icon" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDownModal}
                placeholder="Type to search invoices, customers, products, SKUs, POs..."
                className="search-modal-input"
              />
              {loading && <Loader2 size={18} className="search-spinner" />}
              {query && !loading && (
                <button onClick={() => setQuery('')} className="search-clear-btn">
                  <X size={16} />
                </button>
              )}
              <button onClick={() => setIsOpen(false)} className="search-close-badge">
                ESC
              </button>
            </div>

            {/* Results Body */}
            <div className="search-modal-body">
              {!query.trim() && (
                <div className="search-empty-state">
                  <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#64748B', marginBottom: '12px' }}>
                    Quick Jumps & Shortcuts
                  </div>
                  <div className="search-quick-links">
                    <button onClick={() => { setIsOpen(false); navigate('/pos'); }} className="quick-link-chip">
                      <PlusCircle size={14} color="#059669" /> New Bill
                    </button>
                    <button onClick={() => { setIsOpen(false); navigate('/invoices'); }} className="quick-link-chip">
                      <FileText size={14} color="#2563EB" /> All Invoices & Bills
                    </button>
                    <button onClick={() => { setIsOpen(false); navigate('/customers'); }} className="quick-link-chip">
                      <Users size={14} color="#7C3AED" /> Customer Ledgers
                    </button>
                    <button onClick={() => { setIsOpen(false); navigate('/products'); }} className="quick-link-chip">
                      <Package size={14} color="#D97706" /> Product Catalog
                    </button>
                  </div>
                </div>
              )}

              {query.trim() && totalResultsCount === 0 && !loading && (
                <div className="search-no-results">
                  <Package size={32} color="#94A3B8" />
                  <p>No matching bills, customers, or SKUs found for "<strong>{query}</strong>"</p>
                </div>
              )}

              {totalResultsCount > 0 && (
                <div className="search-results-list">
                  {/* Invoices Group */}
                  {results.invoices && results.invoices.length > 0 && (
                    <div className="search-group">
                      <div className="search-group-title">
                        <FileText size={14} /> Bills & Invoices ({results.invoices.length})
                      </div>
                      {results.invoices.map((inv) => {
                        const globalIdx = allFlattenedItems.findIndex(
                          (item) => item._type === 'invoice' && item.id === inv.id
                        );
                        const isSelected = globalIdx === selectedIndex;
                        return (
                          <div
                            key={`inv-${inv.id}`}
                            className={`search-result-item ${isSelected ? 'selected' : ''}`}
                            onClick={() => handleSelectItem({ ...inv, path: '/invoices' })}
                            onMouseEnter={() => setSelectedIndex(globalIdx)}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              <div className="result-icon-box inv">
                                <FileText size={16} />
                              </div>
                              <div>
                                <div className="result-title">{inv.invoice_number}</div>
                                <div className="result-subtitle">{inv.customer_name} {inv.customer_phone ? `(${inv.customer_phone})` : ''}</div>
                              </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div className="result-price">₹{inv.total_amount.toFixed(2)}</div>
                              <span className={`badge-smart ${inv.payment_status === 'paid' ? 'badge-paid' : 'badge-overdue'}`}>
                                {inv.payment_status?.toUpperCase() || 'UNPAID'}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Customers Group */}
                  {results.customers && results.customers.length > 0 && (
                    <div className="search-group">
                      <div className="search-group-title">
                        <Users size={14} /> Customers ({results.customers.length})
                      </div>
                      {results.customers.map((cust) => {
                        const globalIdx = allFlattenedItems.findIndex(
                          (item) => item._type === 'customer' && item.id === cust.id
                        );
                        const isSelected = globalIdx === selectedIndex;
                        return (
                          <div
                            key={`cust-${cust.id}`}
                            className={`search-result-item ${isSelected ? 'selected' : ''}`}
                            onClick={() => handleSelectItem({ ...cust, path: '/customers' })}
                            onMouseEnter={() => setSelectedIndex(globalIdx)}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              <div className="result-icon-box cust">
                                <Users size={16} />
                              </div>
                              <div>
                                <div className="result-title">{cust.name}</div>
                                <div className="result-subtitle">{cust.phone || cust.email || 'No contact details'}</div>
                              </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ fontSize: '0.8rem', color: '#64748B' }}>Outstanding</div>
                              <div className="result-price" style={{ color: cust.outstanding_balance > 0 ? '#DC2626' : '#166534' }}>
                                ₹{cust.outstanding_balance.toFixed(2)}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Products Group */}
                  {results.products && results.products.length > 0 && (
                    <div className="search-group">
                      <div className="search-group-title">
                        <Package size={14} /> Products & SKUs ({results.products.length})
                      </div>
                      {results.products.map((prod) => {
                        const globalIdx = allFlattenedItems.findIndex(
                          (item) => item._type === 'product' && item.id === prod.id
                        );
                        const isSelected = globalIdx === selectedIndex;
                        return (
                          <div
                            key={`prod-${prod.id}`}
                            className={`search-result-item ${isSelected ? 'selected' : ''}`}
                            onClick={() => handleSelectItem({ ...prod, path: '/products' })}
                            onMouseEnter={() => setSelectedIndex(globalIdx)}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              <div className="result-icon-box prod">
                                <Package size={16} />
                              </div>
                              <div>
                                <div className="result-title">{prod.name}</div>
                                <div className="result-subtitle">
                                  {prod.sku ? `SKU: ${prod.sku} · ` : ''}{prod.category || 'General'}
                                </div>
                              </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div className="result-price">₹{prod.price.toFixed(2)}</div>
                              <div style={{ fontSize: '0.75rem', color: prod.stock <= 5 ? '#DC2626' : '#166534', fontWeight: '600' }}>
                                Stock: {prod.stock} {prod.uom}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer Nav Tips */}
            <div className="search-modal-footer">
              <div style={{ display: 'flex', gap: '16px', fontSize: '0.75rem', color: '#64748B' }}>
                <span><kbd className="search-kbd">↑</kbd> <kbd className="search-kbd">↓</kbd> Navigate</span>
                <span><kbd className="search-kbd">↵</kbd> Select</span>
                <span><kbd className="search-kbd">ESC</kbd> Close</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
