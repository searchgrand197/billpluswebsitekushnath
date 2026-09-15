import React, { useEffect, useState } from 'react';
import { getDuesSummary, createPayment, getPayments } from '../api';
import { CreditCard, Plus, CheckCircle, AlertTriangle, Search } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import { paymentModeStyle } from './poUtils';

export default function DuesCollections() {
  const [duesData, setDuesData] = useState(null);
  const [payments, setPayments] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [referenceNo, setReferenceNo] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = () => {
    getDuesSummary().then((res) => setDuesData(res.data));
    getPayments()
      .then((res) => {
        setPayments(res.data.results || res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  };

  const handleRecordPayment = (e) => {
    e.preventDefault();
    if (!selectedCustomerId) {
      toast.showWarning('Please select a customer for the payment entry.');
      return;
    }
    if (!paymentAmount || Number(paymentAmount) <= 0) {
      toast.showWarning('Please enter a valid positive payment amount.');
      return;
    }

    createPayment({
      customer: selectedCustomerId,
      amount: Number(paymentAmount),
      payment_method: paymentMethod,
      reference_number: referenceNo,
      payment_date: new Date().toISOString().split('T')[0],
    })
      .then(() => {
        toast.showSuccess(`Payment entry of ₹${Number(paymentAmount).toFixed(2)} recorded successfully.`);
        setShowPaymentModal(false);
        setPaymentAmount('');
        setReferenceNo('');
        setSelectedCustomerId('');
        fetchData();
      })
      .catch((err) => {
        console.error(err);
        toast.showError(err.response?.data?.detail || err.response?.data?.amount?.[0] || 'Failed to record payment entry.');
      });
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Dues & Payment Receipts...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Dues & Payment Collections</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748B' }}>Accounts receivable debt balances and collection receipt entries.</p>
        </div>
        <button onClick={() => setShowPaymentModal(true)} className="btn-smart btn-primary-smart">
          <Plus size={18} /> Record Payment Entry
        </button>
      </div>

      {/* Dues Summary Stat */}
      <div className="stat-card" style={{ marginBottom: '24px', maxWidth: '400px' }}>
        <div>
          <div className="stat-label">Total Outstanding Debt</div>
          <div className="stat-value" style={{ color: '#DC2626' }}>
            ₹{Number(duesData?.total_outstanding || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <small style={{ fontSize: '0.75rem', color: '#64748B' }}>{duesData?.customers?.length || 0} Parties with Outstanding Balance</small>
        </div>
        <div className="stat-icon icon-orange">
          <AlertTriangle size={24} />
        </div>
      </div>

      {/* Debtors List */}
      <div className="smart-card" style={{ marginBottom: '24px' }}>
        <div className="card-header-smart" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontWeight: '700' }}>Parties with Outstanding Dues</div>
          <div style={{ position: 'relative', width: '280px' }}>
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Search debtor name or phone..."
              className="form-control-smart"
              style={{ paddingLeft: '34px', height: '34px', fontSize: '0.85rem' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
        <table className="smart-table">
          <thead>
            <tr>
              <th>Customer Name</th>
              <th>Phone</th>
              <th>Outstanding Debt</th>
              <th style={{ textAlign: 'center' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {duesData?.customers
              ?.filter((c) =>
                c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                (c.phone && c.phone.includes(searchTerm))
              )
              ?.map((c) => (
                <tr key={c.id}>
                  <td style={{ fontWeight: '700', color: '#0F172A' }}>{c.name}</td>
                  <td>{c.phone || '-'}</td>
                  <td style={{ fontWeight: '800', color: '#DC2626' }}>₹{Number(c.outstanding_balance).toFixed(2)}</td>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      onClick={() => {
                        setSelectedCustomerId(c.id);
                        setShowPaymentModal(true);
                      }}
                      className="btn-smart btn-primary-smart"
                      style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                    >
                      Receive Payment
                    </button>
                  </td>
                </tr>
              ))}
            {(!duesData?.customers || duesData.customers.length === 0) && (
              <tr>
                <td colSpan="4" style={{ textAlign: 'center', padding: '24px', color: '#166534', fontWeight: '600' }}>
                  ✓ All customer balances are clear! Zero outstanding debt.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Payment Receipts History */}
      <div className="smart-card">
        <div className="card-header-smart">
          <div style={{ fontWeight: '700' }}>Payment Collection Stream</div>
        </div>
        <table className="smart-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Method</th>
              <th>Ref / Txn #</th>
              <th>Amount Received</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td style={{ fontWeight: '700', color: '#0F172A' }}>{p.customer_name}</td>
                <td>
                <td>
                  {(() => {
                    const pm = paymentModeStyle(p.payment_method);
                    return (
                      <span className="badge-smart" style={{ backgroundColor: pm.bg, color: pm.color, border: `1px solid ${pm.border}` }}>
                        {pm.label}
                      </span>
                    );
                  })()}
                </td>
                </td>
                <td>{p.reference_number || '-'}</td>
                <td style={{ fontWeight: '800', color: '#15803D' }}>₹{Number(p.amount).toFixed(2)}</td>
                <td>{p.payment_date}</td>
              </tr>
            ))}
            {payments.length === 0 && (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '24px', color: '#94A3B8' }}>
                  No payment receipts recorded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Record Payment Modal */}
      {showPaymentModal && (
        <div className="modal-backdrop">
          <div className="modal-content-smart">
            <h3 style={{ fontWeight: '700', marginBottom: '16px' }}>Record Payment Entry</h3>
            <form onSubmit={handleRecordPayment}>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: '600', color: '#64748B', display: 'block', marginBottom: '4px' }}>Select Debtor Customer</label>
                <select className="form-control-smart" required value={selectedCustomerId} onChange={(e) => setSelectedCustomerId(e.target.value)}>
                  <option value="">-- Choose Customer --</option>
                  {duesData?.customers?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} (Due: ₹{Number(c.outstanding_balance).toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: '600', color: '#64748B', display: 'block', marginBottom: '4px' }}>Amount Collected (₹)</label>
                <input type="number" step="0.01" className="form-control-smart" required value={paymentAmount} onChange={(e) => setPaymentAmount(e.target.value)} />
              </div>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: '600', color: '#64748B', display: 'block', marginBottom: '4px' }}>Payment Mode</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 6 }}>
                  {[
                    { id: 'cash', label: 'Cash' },
                    { id: 'upi', label: 'UPI' },
                    { id: 'bank_transfer', label: 'Bank' },
                    { id: 'other', label: 'Other' },
                  ].map((m) => {
                    const st = paymentModeStyle(m.id);
                    const on = paymentMethod === m.id;
                    return (
                      <button key={m.id} type="button" className="btn-smart" onClick={() => setPaymentMethod(m.id)} style={{ background: st.bg, color: st.color, border: on ? `2px solid ${st.color}` : `1px solid ${st.border}`, fontWeight: 800, fontSize: 12, justifyContent: 'center' }}>
                        {m.label}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: '600', color: '#64748B', display: 'block', marginBottom: '4px' }}>Reference / UPI UTR #</label>
                <input type="text" className="form-control-smart" value={referenceNo} onChange={(e) => setReferenceNo(e.target.value)} />
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn-smart btn-secondary-smart" onClick={() => setShowPaymentModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-smart btn-primary-smart">
                  Save Receipt Entry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
