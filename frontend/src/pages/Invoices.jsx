import React, { useEffect, useState } from 'react';
import { getInvoices, cancelInvoice } from '../api';
import { FileText, Printer, Search, Download, Ban, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import ConfirmationModal from '../components/ConfirmationModal';
import { useToast } from '../components/ToastContext';
import { paymentModeStyle } from './poUtils';

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Cancel Modal State
  const [cancelModalInvoice, setCancelModalInvoice] = useState(null);
  const [cancelling, setCancelling] = useState(false);

  const toast = useToast();

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = () => {
    getInvoices()
      .then((res) => {
        setInvoices(res.data.results || res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  };

  const handleConfirmCancelInvoice = () => {
    if (!cancelModalInvoice) return;
    setCancelling(true);
    cancelInvoice(cancelModalInvoice.id)
      .then(() => {
        toast.showSuccess(`Invoice #${cancelModalInvoice.invoice_number} cancelled. Stock restored and ledger updated.`);
        setCancelling(false);
        setCancelModalInvoice(null);
        fetchInvoices();
      })
      .catch((err) => {
        setCancelling(false);
        toast.showError(err.response?.data?.error || 'Failed to cancel invoice.');
      });
  };

  const filteredInvoices = invoices.filter((inv) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      inv.invoice_number.toLowerCase().includes(term) ||
      (inv.customer_name && inv.customer_name.toLowerCase().includes(term)) ||
      (inv.customer_phone && inv.customer_phone.includes(term)) ||
      (inv.payment_status && inv.payment_status.toLowerCase().includes(term)) ||
      String(inv.total_amount).includes(term);
    const matchesStatus = statusFilter === 'all' || inv.payment_status === statusFilter || inv.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Sales Invoices...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Sales Bills & Invoices History</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748B' }}>View, filter, download, print, or cancel sales transactions.</p>
        </div>
        <Link to="/pos" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }}>
          + Create New Bill
        </Link>
      </div>

      <div className="smart-card">
        {/* Filters */}
        <div className="card-header-smart" style={{ gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', width: '300px' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Search by Bill #, Customer, or Amount..."
              className="form-control-smart"
              style={{ paddingLeft: '38px', height: '38px', backgroundColor: '#F8FAFC' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            {['all', 'paid', 'credit', 'partially_paid', 'cancelled'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: statusFilter === st ? '1px solid #059669' : '1px solid #E2E8F0',
                  backgroundColor: statusFilter === st ? '#ECFDF5' : '#FFFFFF',
                  color: statusFilter === st ? '#047857' : '#64748B',
                  fontSize: '0.8rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                }}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Invoice Table */}
        <table className="smart-table">
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Date</th>
              <th>Customer</th>
              <th>Subtotal</th>
              <th>GST Tax</th>
              <th>Total Amount</th>
              <th>Pay Mode</th>
              <th>Status</th>
              <th style={{ textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredInvoices.map((inv) => {
              const isCancelled = inv.status === 'cancelled';
              return (
                <tr key={inv.id} style={{ opacity: isCancelled ? 0.6 : 1 }}>
                  <td style={{ fontWeight: '700', color: isCancelled ? '#64748B' : '#059669' }}>
                    {inv.invoice_number}
                  </td>
                  <td>{inv.invoice_date}</td>
                  <td style={{ fontWeight: '600' }}>{inv.customer_name || 'Walk-in Customer'}</td>
                  <td>₹{Number(inv.subtotal).toFixed(2)}</td>
                  <td>₹{(Number(inv.cgst_amount || 0) + Number(inv.sgst_amount || 0)).toFixed(2)}</td>
                  <td style={{ fontWeight: '800', color: '#0F172A' }}>₹{Number(inv.total_amount).toFixed(2)}</td>
                  <td>
                    {(() => {
                      const pm = paymentModeStyle(inv.status === 'credit' ? 'credit' : inv.payment_method);
                      return (
                        <span className="badge-smart" style={{ backgroundColor: pm.bg, color: pm.color, border: `1px solid ${pm.border}` }}>
                          {pm.label}
                        </span>
                      );
                    })()}
                  </td>
                  <td>
                    <span className={`badge-smart badge-${inv.status === 'paid' ? 'paid' : inv.status === 'cancelled' ? 'overdue' : 'pending'}`}>
                      {inv.status?.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ display: 'inline-flex', gap: '6px' }}>
                      <a
                        href={`http://localhost:8000/billing/invoices/${inv.id}/print/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-smart btn-outline-smart"
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      >
                        <Printer size={14} /> Print
                      </a>
                      <a
                        href={`http://localhost:8000/billing/invoices/${inv.id}/pdf/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-smart btn-secondary-smart"
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      >
                        <Download size={14} /> PDF
                      </a>
                      {!isCancelled && (
                        <button
                          onClick={() => setCancelModalInvoice(inv)}
                          className="btn-smart btn-outline-smart"
                          style={{ padding: '4px 8px', fontSize: '0.75rem', color: '#DC2626', borderColor: '#FCA5A5' }}
                          title="Cancel Invoice & Restore Stock"
                        >
                          <Ban size={14} /> Cancel
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {filteredInvoices.length === 0 && (
              <tr>
                <td colSpan="9" style={{ textAlign: 'center', padding: '32px', color: '#94A3B8' }}>
                  No matching sales invoices found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Confirmation Modal for Cancellation */}
      <ConfirmationModal
        isOpen={Boolean(cancelModalInvoice)}
        onClose={() => setCancelModalInvoice(null)}
        onConfirm={handleConfirmCancelInvoice}
        title="Cancel Invoice?"
        message={`Are you sure you want to cancel Invoice #${cancelModalInvoice?.invoice_number}? Deducted finished product stock will be restored and customer ledger will be adjusted.`}
        confirmText="Yes, Cancel Invoice"
        cancelText="Keep Invoice"
        isDanger={true}
        loading={cancelling}
      />
    </div>
  );
}
