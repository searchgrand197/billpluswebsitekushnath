import React, { useEffect, useState } from 'react';
import { getInvoices, cancelInvoice, addInvoicePayment, getInvoicePayments } from '../api';
import { Printer, Search, Download, Ban, IndianRupee, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import ConfirmationModal from '../components/ConfirmationModal';
import { useToast } from '../components/ToastContext';
import { paymentModeStyle } from './poUtils';

const todayISO = () => new Date().toISOString().split('T')[0];

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const [cancelModalInvoice, setCancelModalInvoice] = useState(null);
  const [cancelling, setCancelling] = useState(false);

  const [paymentInvoice, setPaymentInvoice] = useState(null);
  const [paymentHistory, setPaymentHistory] = useState([]);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentDate, setPaymentDate] = useState(todayISO());
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paymentNotes, setPaymentNotes] = useState('');
  const [paymentRef, setPaymentRef] = useState('');
  const [savingPayment, setSavingPayment] = useState(false);

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

  const openPaymentModal = (inv) => {
    setPaymentInvoice(inv);
    setPaymentAmount('');
    setPaymentDate(todayISO());
    setPaymentMethod(inv.payment_method || 'cash');
    setPaymentNotes('');
    setPaymentRef('');
    setPaymentHistory([]);
    getInvoicePayments(inv.id)
      .then((res) => setPaymentHistory(res.data.results || res.data || []))
      .catch(() => setPaymentHistory([]));
  };

  const closePaymentModal = () => {
    setPaymentInvoice(null);
    setPaymentHistory([]);
  };

  const handleAddPayment = (e) => {
    e.preventDefault();
    if (!paymentInvoice) return;

    const amount = Number(paymentAmount);
    const outstanding = Number(paymentInvoice.outstanding_amount || 0);
    if (!amount || amount <= 0) {
      toast.showWarning('Enter a payment amount greater than zero.');
      return;
    }
    if (amount > outstanding + 0.001) {
      toast.showWarning(`Amount cannot exceed outstanding ₹${outstanding.toFixed(2)}.`);
      return;
    }
    if (!paymentDate) {
      toast.showWarning('Select a payment date.');
      return;
    }

    setSavingPayment(true);
    addInvoicePayment(paymentInvoice.id, {
      amount,
      payment_date: paymentDate,
      payment_method: paymentMethod,
      notes: paymentNotes.trim(),
      reference_number: paymentRef.trim(),
    })
      .then((res) => {
        const updated = res.data?.invoice;
        toast.showSuccess(
          `₹${amount.toFixed(2)} recorded on ${paymentDate}${paymentNotes.trim() ? ` — ${paymentNotes.trim()}` : ''}.`
        );
        setSavingPayment(false);
        if (updated && Number(updated.outstanding_amount || 0) <= 0) {
          closePaymentModal();
        } else if (updated) {
          setPaymentInvoice(updated);
          setPaymentAmount('');
          setPaymentNotes('');
          setPaymentRef('');
          // Keep same date so user can add another payment same day with a new note
          getInvoicePayments(updated.id)
            .then((r) => setPaymentHistory(r.data.results || r.data || []))
            .catch(() => {});
        } else {
          closePaymentModal();
        }
        fetchInvoices();
      })
      .catch((err) => {
        setSavingPayment(false);
        toast.showError(
          err.response?.data?.error ||
            err.response?.data?.detail ||
            'Failed to record payment.'
        );
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

  const canCollect = (inv) =>
    !['cancelled', 'paid'].includes(inv.status) && Number(inv.outstanding_amount || 0) > 0;

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
                  <td style={{ fontWeight: '800', color: '#0F172A' }}>
                    ₹{Number(inv.total_amount).toFixed(2)}
                    {canCollect(inv) && (
                      <div style={{ fontSize: '0.7rem', fontWeight: '600', color: '#B45309', marginTop: '2px' }}>
                        Due ₹{Number(inv.outstanding_amount).toFixed(2)}
                      </div>
                    )}
                  </td>
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
                    <div style={{ display: 'inline-flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'center' }}>
                      {canCollect(inv) && (
                        <button
                          onClick={() => openPaymentModal(inv)}
                          className="btn-smart btn-primary-smart"
                          style={{ padding: '4px 10px', fontSize: '0.75rem', backgroundColor: '#D97706', borderColor: '#D97706' }}
                          title="Add payment against outstanding"
                        >
                          <IndianRupee size={14} /> Add Payment
                        </button>
                      )}
                      <a
                        href={`/billing/invoices/${inv.id}/print/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-smart btn-outline-smart"
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      >
                        <Printer size={14} /> Print
                      </a>
                      <a
                        href={`/billing/invoices/${inv.id}/pdf/`}
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

      {paymentInvoice && (
        <div className="modal-backdrop" onClick={closePaymentModal}>
          <div
            className="smart-card"
            style={{ width: '480px', maxWidth: '94vw', maxHeight: '90vh', overflow: 'auto', margin: '40px auto', padding: '24px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <h2 style={{ fontSize: '1.15rem', fontWeight: '800', color: '#0F172A', margin: 0 }}>
                  Add Payment — {paymentInvoice.invoice_number}
                </h2>
                <p style={{ fontSize: '0.8rem', color: '#64748B', margin: '4px 0 0' }}>
                  {paymentInvoice.customer_name || 'Walk-in Customer'} · Outstanding{' '}
                  <strong style={{ color: '#B45309' }}>₹{Number(paymentInvoice.outstanding_amount || 0).toFixed(2)}</strong>
                </p>
              </div>
              <button type="button" onClick={closePaymentModal} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94A3B8' }}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleAddPayment}>
              <div style={{ display: 'grid', gap: '12px' }}>
                <div>
                  <label className="form-field-label">Amount (₹)</label>
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    required
                    className="form-control-smart"
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    placeholder={`Max ${Number(paymentInvoice.outstanding_amount || 0).toFixed(2)}`}
                    autoFocus
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label className="form-field-label">Payment Date</label>
                    <input
                      type="date"
                      required
                      className="form-control-smart"
                      value={paymentDate}
                      onChange={(e) => setPaymentDate(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="form-field-label">Method</label>
                    <select
                      className="form-control-smart"
                      value={paymentMethod}
                      onChange={(e) => setPaymentMethod(e.target.value)}
                    >
                      <option value="cash">Cash</option>
                      <option value="upi">UPI</option>
                      <option value="card">Card</option>
                      <option value="bank_transfer">Bank Transfer</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="form-field-label">Note</label>
                  <input
                    type="text"
                    className="form-control-smart"
                    value={paymentNotes}
                    onChange={(e) => setPaymentNotes(e.target.value)}
                    placeholder="e.g. Part payment via UPI — same day OK"
                  />
                </div>
                <div>
                  <label className="form-field-label">Reference # (optional)</label>
                  <input
                    type="text"
                    className="form-control-smart"
                    value={paymentRef}
                    onChange={(e) => setPaymentRef(e.target.value)}
                    placeholder="UPI / cheque / txn id"
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', marginTop: '18px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn-smart btn-outline-smart" onClick={closePaymentModal} disabled={savingPayment}>
                  Close
                </button>
                <button type="submit" className="btn-smart btn-primary-smart" disabled={savingPayment} style={{ backgroundColor: '#D97706', borderColor: '#D97706' }}>
                  {savingPayment ? 'Saving…' : 'Save Payment'}
                </button>
              </div>
            </form>

            {paymentHistory.length > 0 && (
              <div style={{ marginTop: '20px', borderTop: '1px solid #E2E8F0', paddingTop: '14px' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#475569', marginBottom: '8px' }}>
                  Previous payments on this bill
                </div>
                <table className="smart-table" style={{ fontSize: '0.8rem' }}>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Amount</th>
                      <th>Method</th>
                      <th>Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paymentHistory.map((p) => (
                      <tr key={p.id}>
                        <td>{p.payment_date}</td>
                        <td style={{ fontWeight: '700', color: '#15803D' }}>₹{Number(p.amount).toFixed(2)}</td>
                        <td>{p.payment_method}</td>
                        <td style={{ color: '#64748B' }}>{p.notes || p.reference_number || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
