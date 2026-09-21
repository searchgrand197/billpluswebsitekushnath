import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCustomers, getCustomerLedger, createCustomer, updateCustomer, deleteCustomer, createPayment } from '../api';
import {
  BookOpen, Plus, Search, X, ShoppingCart, Wallet, RotateCcw, FileText,
  Pencil, Eye, Printer, Banknote, Smartphone, Landmark, Trash2,
} from 'lucide-react';
import { useToast } from '../components/ToastContext';
import ConfirmationModal from '../components/ConfirmationModal';
import { paymentModeStyle, INDIAN_STATES } from './poUtils';

const money = (n) =>
  `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const typeStyle = {
  invoice: { bg: '#ECFDF5', color: '#047857', label: 'Sale' },
  payment: { bg: '#DBEAFE', color: '#1D4ED8', label: 'Payment' },
  adjustment: { bg: '#F1F5F9', color: '#475569', label: 'Discount' },
};

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedLedger, setSelectedLedger] = useState(null);
  const toast = useToast();
  const navigate = useNavigate();

  const [showAddModal, setShowAddModal] = useState(false);
  const [editingParty, setEditingParty] = useState(false);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [state, setState] = useState('');
  const [city, setCity] = useState('');
  const [pincode, setPincode] = useState('');
  const [gstin, setGstin] = useState('');

  const [ledgerTab, setLedgerTab] = useState('ledger');
  const [ledgerSearch, setLedgerSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [payAmount, setPayAmount] = useState('');
  const [payDiscount, setPayDiscount] = useState('');
  const [payMethod, setPayMethod] = useState('cash');
  const [payNote, setPayNote] = useState('');
  const [savingPay, setSavingPay] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = () => {
    getCustomers()
      .then((res) => {
        setCustomers(res.data.results || res.data);
        setLoading(false);
      })
      .catch(() => {
        toast.showError('Failed to fetch customer records.');
        setLoading(false);
      });
  };

  const filteredCustomers = customers.filter((c) => {
    const term = searchTerm.toLowerCase();
    return (
      c.name.toLowerCase().includes(term) ||
      (c.phone && c.phone.includes(term)) ||
      (c.email && c.email.toLowerCase().includes(term)) ||
      (c.state && c.state.toLowerCase().includes(term)) ||
      (c.city && c.city.toLowerCase().includes(term)) ||
      (c.pincode && String(c.pincode).includes(term)) ||
      (c.gstin && c.gstin.toLowerCase().includes(term))
    );
  });

  const loadLedger = (custId) => {
    getCustomerLedger(custId)
      .then((res) => {
        setSelectedLedger(res.data);
        setPayAmount('');
        setPayDiscount('');
        setPayNote('');
        setPayMethod('cash');
        setLedgerSearch('');
      })
      .catch(() => toast.showError('Failed to load customer ledger.'));
  };

  const handleOpenLedger = (cust) => loadLedger(cust.id);

  const due = Number(selectedLedger?.summary?.outstanding ?? selectedLedger?.customer?.outstanding_balance ?? 0);
  const received = Number(payAmount) || 0;
  const discount = Number(payDiscount) || 0;
  const newBalance = Math.max(0, due - received - discount);

  const filteredEntries = useMemo(() => {
    const rows = selectedLedger?.ledger_entries || [];
    return rows.filter((e) => {
      const q = ledgerSearch.toLowerCase();
      const text = `${e.invoice_number || ''} ${e.description || ''} ${e.entry_type || ''}`.toLowerCase();
      if (q && !text.includes(q)) return false;
      const d = (e.entry_date || e.created_at || '').slice(0, 10);
      if (dateFrom && d && d < dateFrom) return false;
      if (dateTo && d && d > dateTo) return false;
      return true;
    });
  }, [selectedLedger, ledgerSearch, dateFrom, dateTo]);

  const handleCreateCustomer = (e) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.showWarning('Please enter a customer name.');
      return;
    }
    if (!state.trim()) {
      toast.showWarning('State is required.');
      return;
    }
    const payload = { name, phone, email, address, state, city, pincode, gstin: gstin.trim().toUpperCase() };
    const req = editingParty && selectedLedger?.customer?.id
      ? updateCustomer(selectedLedger.customer.id, payload)
      : createCustomer(payload);
    req
      .then((res) => {
        toast.showSuccess(editingParty ? 'Party updated.' : `Customer '${name}' saved successfully.`);
        setShowAddModal(false);
        setEditingParty(false);
        setName('');
        setPhone('');
        setEmail('');
        setAddress('');
        setState('');
        setCity('');
        setPincode('');
        setGstin('');
        fetchCustomers();
        if (editingParty && selectedLedger) {
          setSelectedLedger({
            ...selectedLedger,
            customer: { ...selectedLedger.customer, ...res.data },
          });
        }
      })
      .catch((err) => {
        toast.showError(
          err.response?.data?.gstin?.[0]
          || err.response?.data?.state?.[0]
          || err.response?.data?.name?.[0]
          || err.response?.data?.detail
          || 'Failed to save customer.',
        );
      });
  };

  const recordPayment = () => {
    if (!selectedLedger?.customer?.id) return;
    if (received <= 0 && discount <= 0) {
      toast.showWarning('Enter amount received or a discount.');
      return;
    }
    if (received + discount > due + 0.009) {
      toast.showWarning('Payment + discount cannot exceed outstanding due.');
      return;
    }
    setSavingPay(true);
    const payload = {
      customer: selectedLedger.customer.id,
      amount: received > 0 ? received : discount,
      discount: received > 0 ? discount : 0,
      payment_method: payMethod === 'bank' ? 'bank_transfer' : payMethod,
      notes: payNote,
      payment_date: new Date().toISOString().split('T')[0],
    };
    if (received <= 0) {
      payload.amount = discount;
      payload.discount = 0;
      payload.notes = `${payNote} Discount allowed`.trim();
      payload.payment_method = 'other';
    }
    createPayment(payload)
      .then(() => {
        toast.showSuccess('Payment recorded. Ledger updated.');
        fetchCustomers();
        loadLedger(selectedLedger.customer.id);
      })
      .catch((err) => toast.showError(err.response?.data?.amount?.[0] || 'Failed to record payment.'))
      .finally(() => setSavingPay(false));
  };

  const whatsappReminder = () => {
    const c = selectedLedger?.customer;
    const digits = String(c?.phone || '').replace(/\D/g, '');
    if (digits.length < 10) {
      toast.showWarning('Add a valid mobile number to send WhatsApp reminder.');
      return;
    }
    const phoneNo = digits.length === 10 ? `91${digits}` : digits;
    const msg = encodeURIComponent(
      `Namaste ${c.name}, your outstanding balance with Billvice is ${money(due)}. Please arrange payment. Thank you.`
    );
    window.open(`https://wa.me/${phoneNo}?text=${msg}`, '_blank');
  };

  const exportPdf = () => window.print();

  const cust = selectedLedger?.customer;
  const summary = selectedLedger?.summary || {};

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Customer Master...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Customers</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748B' }}>Track customer debit/credit transactions, debt balances, and payment statements.</p>
        </div>
        <button onClick={() => {
          setEditingParty(false);
          setName('');
          setPhone('');
          setEmail('');
          setAddress('');
          setState('');
          setCity('');
          setPincode('');
          setGstin('');
          setShowAddModal(true);
        }} className="btn-smart btn-primary-smart">
          <Plus size={18} /> Add New Customer
        </button>
      </div>

      <div className="smart-card">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #E2E8F0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: '400px' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Search by name, phone, GSTIN, state, city, or pincode..."
              className="form-control-smart"
              style={{ paddingLeft: '38px', height: '38px', backgroundColor: '#F8FAFC' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div style={{ fontSize: '0.85rem', color: '#64748B', fontWeight: '600' }}>
            Showing {filteredCustomers.length} of {customers.length} customers
          </div>
        </div>

        <table className="smart-table">
          <thead>
            <tr>
              <th>Customer Name</th>
              <th>Phone</th>
              <th>GST No</th>
              <th>State</th>
              <th>City</th>
              <th>Pincode</th>
              <th>Email</th>
              <th>Outstanding Balance (A/R)</th>
              <th style={{ textAlign: 'center' }}>Ledger Statement</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filteredCustomers.map((c) => (
              <tr key={c.id}>
                <td style={{ fontWeight: '700', color: '#0F172A' }}>{c.name}</td>
                <td>{c.phone || '-'}</td>
                <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{c.gstin || '-'}</td>
                <td>{c.state || '-'}</td>
                <td>{c.city || '-'}</td>
                <td>{c.pincode || '-'}</td>
                <td style={{ color: '#64748B' }}>{c.email || '-'}</td>
                <td style={{ fontWeight: '800', color: Number(c.outstanding_balance) > 0 ? '#DC2626' : '#15803D' }}>
                  {money(c.outstanding_balance)}
                </td>
                <td style={{ textAlign: 'center' }}>
                  <button onClick={() => handleOpenLedger(c)} className="btn-smart btn-outline-smart" style={{ padding: '4px 12px', fontSize: '0.75rem' }}>
                    <BookOpen size={14} /> Open Ledger
                  </button>
                </td>
                <td>
                  <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 8px', color: '#DC2626' }} onClick={() => setDeleteTarget(c)}>
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {filteredCustomers.length === 0 && (
              <tr>
                <td colSpan="10" style={{ textAlign: 'center', padding: '32px', color: '#94A3B8' }}>
                  {searchTerm ? `No customers found matching "${searchTerm}"` : 'No customer records found.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedLedger && (
        <div className="modal-backdrop party-ledger-root" style={{ alignItems: 'stretch', padding: 16, overflow: 'auto' }}>
          <div
            className="modal-content-smart"
            style={{ maxWidth: 1180, width: '100%', margin: 'auto', maxHeight: 'none', padding: 20 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="no-print" style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: '1.45rem', fontWeight: 900, color: '#0F172A', textTransform: 'uppercase' }}>{cust?.name}</div>
                <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
                  CUS-{String(cust?.id || 0).padStart(4, '0')} · {cust?.name} · {cust?.phone || 'No phone'} · Current Due {money(due)}
                  {summary.last_purchase ? ` · Last Purchase ${summary.last_purchase}` : ''} · Bills {summary.bill_count || 0}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn-smart btn-outline-smart"
                  onClick={() => {
                    setEditingParty(true);
                    setName(cust.name || '');
                    setPhone(cust.phone || '');
                    setEmail(cust.email || '');
                    setAddress(cust.address || '');
                    setState(cust.state || '');
                    setCity(cust.city || '');
                    setPincode(cust.pincode || '');
                    setGstin(cust.gstin || '');
                    setShowAddModal(true);
                  }}
                >
                  <Pencil size={14} /> Edit Party
                </button>
                <button onClick={() => setSelectedLedger(null)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}><X size={20} /></button>
              </div>
            </div>

            <div className="no-print" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
              <button className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }} onClick={() => navigate(`/pos?customer=${encodeURIComponent(cust.name)}&phone=${encodeURIComponent(cust.phone || '')}`)}>
                <ShoppingCart size={14} /> New Sale
              </button>
              <button className="btn-smart btn-outline-smart" onClick={() => document.getElementById('pay-amount')?.focus()}>
                <Wallet size={14} /> Receive Payment
              </button>
              <button className="btn-smart btn-outline-smart" onClick={() => { setLedgerTab('returns'); toast.showWarning('Record a sales return by cancelling the original invoice from Sales History.'); }}>
                <RotateCcw size={14} /> Add Return
              </button>
              <button className="btn-smart btn-outline-smart" onClick={whatsappReminder}>WhatsApp Reminder</button>
              <button className="btn-smart btn-outline-smart" onClick={exportPdf}><FileText size={14} /> Export PDF</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
              <div className="smart-card" style={{ padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 800, color: '#64748B' }}>OUTSTANDING BALANCE</div>
                <div style={{ fontSize: '1.35rem', fontWeight: 900, color: '#EA580C' }}>{money(due)}</div>
              </div>
              <div className="smart-card" style={{ padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 800, color: '#64748B' }}>TOTAL SALES</div>
                <div style={{ fontSize: '1.35rem', fontWeight: 900, color: '#0F766E' }}>{money(summary.total_sales)}</div>
              </div>
              <div className="smart-card" style={{ padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 800, color: '#64748B' }}>TOTAL BILLS</div>
                <div style={{ fontSize: '1.35rem', fontWeight: 900 }}>{summary.bill_count || 0}</div>
              </div>
              <div className="smart-card" style={{ padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 800, color: '#64748B' }}>LAST PURCHASE</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>{summary.last_purchase || '—'}</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 280px', gap: 16, alignItems: 'start' }} className="party-ledger-grid">
              <div>
                <div className="no-print" style={{ display: 'flex', gap: 16, borderBottom: '1px solid #E2E8F0', marginBottom: 12 }}>
                  <button type="button" onClick={() => setLedgerTab('ledger')} style={{ border: 'none', background: 'none', padding: '8px 0', fontWeight: 800, color: ledgerTab === 'ledger' ? '#0F766E' : '#94A3B8', borderBottom: ledgerTab === 'ledger' ? '2px solid #0F766E' : '2px solid transparent', cursor: 'pointer' }}>Ledger</button>
                  <button type="button" onClick={() => setLedgerTab('returns')} style={{ border: 'none', background: 'none', padding: '8px 0', fontWeight: 800, color: ledgerTab === 'returns' ? '#0F766E' : '#94A3B8', borderBottom: ledgerTab === 'returns' ? '2px solid #0F766E' : '2px solid transparent', cursor: 'pointer' }}>Returns</button>
                </div>
                {ledgerTab === 'ledger' && (
                  <>
                    <div className="no-print" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
                      <input className="form-control-smart" placeholder="Search bill, description..." value={ledgerSearch} onChange={(e) => setLedgerSearch(e.target.value)} style={{ flex: 1, minWidth: 180 }} />
                      <input type="date" className="form-control-smart" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} style={{ width: 150 }} />
                      <input type="date" className="form-control-smart" value={dateTo} onChange={(e) => setDateTo(e.target.value)} style={{ width: 150 }} />
                    </div>
                    <div style={{ overflowX: 'auto' }}>
                      <table className="smart-table">
                        <thead>
                          <tr style={{ background: '#0F766E' }}>
                            {['Date', 'Bill No.', 'Type', 'Debit', 'Credit', 'Balance', 'Payment Mode', 'Actions'].map((h) => (
                              <th key={h} style={{ color: '#fff', background: '#0F766E' }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {filteredEntries.map((e) => {
                            const st = typeStyle[e.entry_type] || typeStyle.adjustment;
                            return (
                              <tr key={e.id}>
                                <td style={{ whiteSpace: 'nowrap' }}>{e.entry_date || e.created_at}</td>
                                <td style={{ fontWeight: 700 }}>{e.invoice_number || '—'}</td>
                                <td><span className="badge-smart" style={{ backgroundColor: st.bg, color: st.color }}>{st.label}</span></td>
                                <td style={{ color: Number(e.debit) > 0 ? '#B91C1C' : '#94A3B8' }}>{Number(e.debit) > 0 ? money(e.debit) : '—'}</td>
                                <td style={{ color: Number(e.credit) > 0 ? '#047857' : '#94A3B8' }}>{Number(e.credit) > 0 ? money(e.credit) : '—'}</td>
                                <td style={{ fontWeight: 800 }}>{money(e.balance_after)}</td>
                                <td>
                                  {(() => {
                                    const pm = paymentModeStyle(e.payment_mode);
                                    return (
                                      <span className="badge-smart" style={{ backgroundColor: pm.bg, color: pm.color, border: `1px solid ${pm.border}` }}>
                                        {e.payment_mode_label || pm.label}
                                      </span>
                                    );
                                  })()}
                                </td>
                                <td className="no-print">
                                  {e.invoice_id ? (
                                    <span style={{ display: 'inline-flex', gap: 6 }}>
                                      <a href={`/billing/invoices/${e.invoice_id}/print/`} target="_blank" rel="noreferrer" title="View / Print"><Eye size={14} /></a>
                                      <a href={`/billing/invoices/${e.invoice_id}/print/`} target="_blank" rel="noreferrer" title="Print"><Printer size={14} /></a>
                                    </span>
                                  ) : '—'}
                                </td>
                              </tr>
                            );
                          })}
                          {filteredEntries.length === 0 && (
                            <tr><td colSpan="8" style={{ textAlign: 'center', padding: 24, color: '#94A3B8' }}>No ledger transactions recorded yet.</td></tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
                {ledgerTab === 'returns' && (
                  <div style={{ padding: 24, color: '#64748B', fontSize: 14 }}>
                    Sales returns are handled by cancelling the original invoice in Sales History. Stock is restored and the customer ledger is adjusted.
                  </div>
                )}
              </div>

              <div className="no-print smart-card" style={{ padding: 16 }}>
                <div style={{ fontWeight: 800, marginBottom: 8 }}>Receive Payment</div>
                <div style={{ fontSize: 12, color: '#64748B', marginBottom: 8 }}>Current Due</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 900, color: '#EA580C', marginBottom: 12 }}>{money(due)}</div>
                <label className="pos-field-label">Amount Received</label>
                <input id="pay-amount" type="number" min="0" step="0.01" className="form-control-smart" value={payAmount} onChange={(e) => setPayAmount(e.target.value)} style={{ marginBottom: 8 }} />
                <label className="pos-field-label">Discount in ₹</label>
                <input type="number" min="0" step="0.01" className="form-control-smart" value={payDiscount} onChange={(e) => setPayDiscount(e.target.value)} style={{ marginBottom: 8 }} />
                <div style={{ fontSize: 11, fontWeight: 800, color: '#64748B', marginBottom: 6 }}>PAYMENT MODE</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 6, marginBottom: 10 }}>
                  {[
                    { id: 'cash', label: 'Cash', icon: Banknote },
                    { id: 'upi', label: 'UPI', icon: Smartphone },
                    { id: 'bank', label: 'Bank', icon: Landmark },
                    { id: 'other', label: 'Other', icon: FileText },
                  ].map((m) => {
                    const st = paymentModeStyle(m.id);
                    const on = payMethod === m.id;
                    return (
                    <button key={m.id} type="button" className="btn-smart" onClick={() => setPayMethod(m.id)} style={{ background: st.bg, border: on ? `2px solid ${st.color}` : `1px solid ${st.border}`, color: st.color, padding: '8px 4px', fontSize: 12, fontWeight: 800 }}>
                      <m.icon size={14} /> {m.label}
                    </button>
                    );
                  })}
                </div>
                <div style={{ display: 'flex', gap: 6, marginBottom: 10, fontSize: 12 }}>
                  <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 8px' }} onClick={() => setPayAmount(String(due.toFixed(2)))}>Full Amount</button>
                  <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 8px' }} onClick={() => setPayAmount(String((due / 2).toFixed(2)))}>Half Amount</button>
                  <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 8px' }} onClick={() => { setPayAmount(''); setPayDiscount(''); }}>Clear</button>
                </div>
                <label className="pos-field-label">Note</label>
                <textarea className="form-control-smart" rows={2} value={payNote} onChange={(e) => setPayNote(e.target.value)} />
                <div style={{ marginTop: 10, fontSize: 12, fontWeight: 800 }}>NEW BALANCE: <span style={{ color: '#EA580C' }}>{money(newBalance)}</span></div>
                <button disabled={savingPay || due <= 0} className="btn-smart btn-primary-smart" style={{ width: '100%', marginTop: 12, backgroundColor: '#059669' }} onClick={recordPayment}>
                  Record Payment
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showAddModal && (
        <div className="modal-backdrop" style={{ zIndex: 80 }}>
          <div className="modal-content-smart">
            <h3 style={{ fontWeight: '700', marginBottom: '16px' }}>{editingParty ? 'Edit Party' : 'Create New Customer'}</h3>
            <form onSubmit={handleCreateCustomer}>
              <div className="form-field">
                <label className="form-field-label" htmlFor="cust-name">Customer Name *</label>
                <input id="cust-name" type="text" className="form-control-smart" required placeholder="Full name or business name" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="form-field">
                <label className="form-field-label" htmlFor="cust-phone">Phone</label>
                <input id="cust-phone" type="text" className="form-control-smart" placeholder="10-digit mobile number" maxLength={10} value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>
              <div className="form-field">
                <label className="form-field-label" htmlFor="cust-email">Email</label>
                <input id="cust-email" type="email" className="form-control-smart" placeholder="email@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <div className="form-field">
                <label className="form-field-label" htmlFor="cust-gstin">GST No (optional)</label>
                <input id="cust-gstin" type="text" className="form-control-smart" placeholder="15-character GSTIN e.g. 06ABCDE1234F1Z5" maxLength={15} value={gstin} onChange={(e) => setGstin(e.target.value.toUpperCase())} style={{ textTransform: 'uppercase' }} />
              </div>
              <div className="form-field">
                <label className="form-field-label" htmlFor="cust-state">State *</label>
                <select id="cust-state" className="form-control-smart" required value={state} onChange={(e) => setState(e.target.value)}>
                  <option value="">Select state</option>
                  {INDIAN_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div className="form-field" style={{ marginBottom: 0 }}>
                  <label className="form-field-label" htmlFor="cust-city">City</label>
                  <input id="cust-city" type="text" className="form-control-smart" placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
                </div>
                <div className="form-field" style={{ marginBottom: 0 }}>
                  <label className="form-field-label" htmlFor="cust-pincode">Pincode</label>
                  <input id="cust-pincode" type="text" className="form-control-smart" placeholder="6-digit pincode" maxLength={6} value={pincode} onChange={(e) => setPincode(e.target.value)} />
                </div>
              </div>
              <div className="form-field" style={{ marginBottom: 20 }}>
                <label className="form-field-label" htmlFor="cust-address">Address</label>
                <textarea id="cust-address" className="form-control-smart" rows="2" placeholder="Street, area, landmark…" value={address} onChange={(e) => setAddress(e.target.value)} />
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn-smart btn-secondary-smart" onClick={() => { setShowAddModal(false); setEditingParty(false); }}>Cancel</button>
                <button type="submit" className="btn-smart btn-primary-smart">{editingParty ? 'Save Party' : 'Save Customer'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
      <ConfirmationModal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete customer"
        message={`Delete “${deleteTarget?.name || ''}”? Payments and ledger rows for this party will also be removed.`}
        confirmText="Delete"
        isDanger
        loading={deleting}
        onConfirm={() => {
          setDeleting(true);
          deleteCustomer(deleteTarget.id)
            .then(() => {
              toast.showSuccess('Customer deleted.');
              setDeleteTarget(null);
              if (selectedLedger?.customer?.id === deleteTarget.id) setSelectedLedger(null);
              fetchCustomers();
            })
            .catch((err) => toast.showError(err.response?.data?.error || 'Could not delete customer.'))
            .finally(() => setDeleting(false));
        }}
      />
      <style>{`
        @media (max-width: 900px) {
          .party-ledger-grid { grid-template-columns: 1fr !important; }
        }
        @media print {
          .no-print, .sidebar, .navbar { display: none !important; }
          .modal-backdrop { position: static; background: #fff; padding: 0; }
        }
      `}</style>
    </div>
  );
}
