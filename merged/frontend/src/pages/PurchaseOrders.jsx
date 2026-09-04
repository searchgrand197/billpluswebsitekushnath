import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { getPurchaseOrders, getPurchaseStats, duplicatePurchaseOrder, cancelPurchaseOrder } from '../api';
import { Plus, Search, Truck, FileText, PackageCheck, Ban, IndianRupee, MoreHorizontal } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import ConfirmationModal from '../components/ConfirmationModal';
import { money, STATUS_STYLE, statusLabel } from './poUtils';

export default function PurchaseOrders() {
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [menuId, setMenuId] = useState(null);
  const [cancelPo, setCancelPo] = useState(null);
  const [cancelReason, setCancelReason] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const statusFilter = searchParams.get('status') || '';
  const navigate = useNavigate();
  const toast = useToast();

  const load = () => {
    const qs = new URLSearchParams();
    if (searchTerm) qs.set('search', searchTerm);
    if (statusFilter) qs.set('status', statusFilter);
    if (dateFrom) qs.set('date_from', dateFrom);
    if (dateTo) qs.set('date_to', dateTo);
    const suffix = qs.toString() ? `?${qs}` : '';
    Promise.all([getPurchaseOrders(suffix), getPurchaseStats()])
      .then(([poRes, stRes]) => {
        setOrders(poRes.data.results || poRes.data);
        setStats(stRes.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [statusFilter]);

  const cards = [
    { key: '', label: 'Total Purchase Orders', value: stats?.total, icon: FileText, color: '#0F172A' },
    { key: 'draft', label: 'Draft', value: stats?.draft, icon: FileText, color: '#475569' },
    { key: 'pending_approval', label: 'Pending Approval', value: stats?.pending_approval, icon: FileText, color: '#7C3AED' },
    { key: 'ordered', label: 'Ordered', value: stats?.ordered, icon: Truck, color: '#1D4ED8' },
    { key: 'partially_received', label: 'Partially Received', value: stats?.partially_received, icon: PackageCheck, color: '#B45309' },
    { key: 'received', label: 'Fully Received', value: stats?.received, icon: PackageCheck, color: '#047857' },
    { key: 'cancelled', label: 'Cancelled', value: stats?.cancelled, icon: Ban, color: '#B91C1C' },
    { key: 'value', label: 'Active Purchase Value', value: money(stats?.total_value), icon: IndianRupee, color: '#059669', filter: '' },
  ];

  const exportCsv = () => {
    const header = ['PO Number', 'Date', 'Supplier', 'GSTIN', 'Taxable', 'GST', 'Grand Total', 'Status'];
    const rows = orders.map((po) => [
      po.order_number, po.order_date, po.supplier_name, po.supplier_gstin,
      po.taxable_amount, po.gst_total, po.total_amount, po.status,
    ]);
    const csv = [header, ...rows].map((r) => r.map((c) => `"${c ?? ''}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'purchase-orders.csv';
    a.click();
  };

  const handleDuplicate = (id) => {
    duplicatePurchaseOrder(id).then((res) => {
      toast.showSuccess(`Draft ${res.data.order_number} created.`);
      navigate(`/purchase-orders/${res.data.id}/edit`);
    }).catch((e) => toast.showError(e.response?.data?.error || 'Duplicate failed.'));
  };

  const confirmCancel = () => {
    if (!cancelReason.trim()) {
      toast.showError('Cancellation reason is required.');
      return;
    }
    cancelPurchaseOrder(cancelPo.id, { reason: cancelReason }).then(() => {
      toast.showSuccess('Purchase Order cancelled.');
      setCancelPo(null);
      setCancelReason('');
      load();
    }).catch((e) => toast.showError(e.response?.data?.error || 'Cancel failed.'));
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading purchase orders...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Purchase Orders</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748B' }}>Ayurvedic procurement — stock is updated only when goods are received.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <Link to="/purchase-inward" className="btn-smart btn-outline-smart" style={{ textDecoration: 'none' }}>Pending inward</Link>
          <Link to="/suppliers" className="btn-smart btn-outline-smart" style={{ textDecoration: 'none' }}>Suppliers</Link>
          <Link to="/purchase-orders/create" className="btn-smart btn-primary-smart" style={{ textDecoration: 'none', backgroundColor: '#059669' }}>
            <Plus size={16} /> Create Purchase Order
          </Link>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginBottom: '20px' }}>
        {cards.map((c) => (
          <button
            key={c.label}
            type="button"
            onClick={() => setSearchParams(c.key ? { status: c.key } : {})}
            className="smart-card"
            style={{
              padding: '14px',
              textAlign: 'left',
              border: statusFilter === (c.filter ?? c.key) ? '2px solid #059669' : '1px solid #E2E8F0',
              cursor: 'pointer',
              background: '#fff',
            }}
          >
            <div style={{ fontSize: '0.7rem', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>{c.label}</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 900, color: c.color, marginTop: 4 }}>{c.value ?? 0}</div>
          </button>
        ))}
      </div>

      <div className="smart-card">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #E2E8F0', display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: '1 1 240px' }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input className="form-control-smart" style={{ paddingLeft: 36 }} placeholder="PO number, supplier, GSTIN" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          </div>
          <input type="date" className="form-control-smart" style={{ width: 150 }} value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <input type="date" className="form-control-smart" style={{ width: 150 }} value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <button type="button" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }} onClick={load}>Search</button>
          <button type="button" className="btn-smart btn-outline-smart" onClick={() => { setSearchTerm(''); setDateFrom(''); setDateTo(''); setSearchParams({}); setTimeout(load, 0); }}>Reset</button>
          <button type="button" className="btn-smart btn-outline-smart" onClick={exportCsv}>Export CSV</button>
          <button type="button" className="btn-smart btn-outline-smart" onClick={() => window.print()}>Print</button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="smart-table">
            <thead>
              <tr>
                <th>PO Number</th>
                <th>PO Date</th>
                <th>Supplier</th>
                <th>GSTIN</th>
                <th>Expected</th>
                <th>Items</th>
                <th>Taxable</th>
                <th>GST</th>
                <th>Grand Total</th>
                <th>Pending</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {orders.map((po) => {
                const st = STATUS_STYLE[po.status] || STATUS_STYLE.draft;
                return (
                  <tr key={po.id}>
                    <td style={{ fontWeight: 800, color: '#059669' }}>
                      <Link to={`/purchase-orders/${po.id}`} style={{ color: 'inherit', textDecoration: 'none' }}>{po.order_number}</Link>
                    </td>
                    <td>{po.order_date}</td>
                    <td style={{ fontWeight: 600 }}>{po.supplier_name}</td>
                    <td>{po.supplier_gstin || '—'}</td>
                    <td>{po.expected_delivery_date || '—'}</td>
                    <td>{po.item_count}</td>
                    <td>{money(po.taxable_amount)}</td>
                    <td>{money(po.gst_total)}</td>
                    <td style={{ fontWeight: 800 }}>{money(po.total_amount)}</td>
                    <td>{money(po.pending_amount)}</td>
                    <td>
                      <span className="badge-smart" style={{ backgroundColor: st.bg, color: st.color }}>{statusLabel(po.status)}</span>
                    </td>
                    <td style={{ position: 'relative' }}>
                      <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 8px' }} onClick={() => setMenuId(menuId === po.id ? null : po.id)}>
                        <MoreHorizontal size={16} />
                      </button>
                      {menuId === po.id && (
                        <div className="pos-search-menu" style={{ right: 0, left: 'auto', minWidth: 160, top: '100%' }}>
                          <button className="pos-search-option" onClick={() => navigate(`/purchase-orders/${po.id}`)}>View</button>
                          {['draft', 'ordered'].includes(po.status) && (
                            <button className="pos-search-option" onClick={() => navigate(`/purchase-orders/${po.id}/edit`)}>Edit</button>
                          )}
                          <button className="pos-search-option" onClick={() => handleDuplicate(po.id)}>Duplicate</button>
                            <button className="pos-search-option" onClick={() => navigate(`/purchase-orders/${po.id}?print=1`)}>Print / PDF</button>
                          {['ordered', 'partially_received'].includes(po.status) && (
                            <button className="pos-search-option" onClick={() => navigate(`/purchase-orders/${po.id}?receive=1`)}>Receive</button>
                          )}
                          {!['cancelled', 'received', 'closed'].includes(po.status) && (
                            <button className="pos-search-option" style={{ color: '#B91C1C' }} onClick={() => { setCancelPo(po); setMenuId(null); }}>Cancel</button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
              {orders.length === 0 && (
                <tr><td colSpan="12" style={{ textAlign: 'center', padding: 32, color: '#94A3B8' }}>No purchase orders found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmationModal
        isOpen={!!cancelPo}
        onClose={() => setCancelPo(null)}
        onConfirm={confirmCancel}
        isDanger
        title="Cancel Purchase Order?"
        message={
          <div>
            <p>Are you sure you want to cancel {cancelPo?.order_number}? Received stock is not reversed.</p>
            <textarea className="form-control-smart" style={{ marginTop: 10 }} rows={3} placeholder="Cancellation reason *" value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} />
          </div>
        }
        confirmText="Cancel PO"
      />
    </div>
  );
}
