import React, { useEffect, useState, useRef } from 'react';
import { getProducts, getCustomers, getCompanySettings, createInvoicePos, createCustomer, createProduct } from '../api';
import { useSearchParams } from 'react-router-dom';
import { User, Calendar, Clock, Plus, Printer, FileText, RotateCcw, CheckCircle, Trash2, Banknote, Smartphone, Landmark, X, ChevronDown, UserPlus } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import PricingGstCard from '../components/PricingGstCard';
import { beforeFromInclusive, sellingGstMath, normalizeGstRate, paymentModeStyle, INDIAN_STATES, saleIsInterstate } from './poUtils';

const POS_DRAFT_KEY = 'billvice_pos_draft';

function readPosDraft() {
  try {
    return JSON.parse(localStorage.getItem(POS_DRAFT_KEY) || 'null');
  } catch {
    return null;
  }
}

function writePosDraft(data) {
  try {
    const hasItems = Array.isArray(data.rows) && data.rows.some((r) => r.product_id);
    const hasWork = hasItems || (data.customerName && data.customerName.trim()) || Number(data.extraDiscount);
    if (hasWork) localStorage.setItem(POS_DRAFT_KEY, JSON.stringify(data));
    else localStorage.removeItem(POS_DRAFT_KEY);
  } catch {
    /* ignore quota */
  }
}

function clearPosDraft() {
  try {
    localStorage.removeItem(POS_DRAFT_KEY);
  } catch {
    /* ignore */
  }
}

function emptyPosRow(id = 1, defaultGst = 0) {
  return {
    id,
    product_id: '',
    product_name: '',
    pack: '1 Unit',
    hsn: '',
    gst_rate: Number(defaultGst) || 0,
    mrp: 0,
    qty: 1,
    loose: 0,
    disc: 0,
    rate: 0,
    amount: 0,
  };
}

export default function PosBilling() {
  const savedDraft = readPosDraft() || {};
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [companySettings, setCompanySettings] = useState(null);
  const toast = useToast();
  const [searchParams] = useSearchParams();

  // Top bar fields
  const [customerName, setCustomerName] = useState(savedDraft.customerName || '');
  const [customerPhone, setCustomerPhone] = useState(savedDraft.customerPhone || '');
  const [billNumber, setBillNumber] = useState('QUICK');
  const [billDate, setBillDate] = useState(savedDraft.billDate || new Date().toISOString().split('T')[0]);
  const [billTime, setBillTime] = useState(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));

  // Table items rows — always keep at least one blank line ready
  const [rows, setRows] = useState(
    Array.isArray(savedDraft.rows) && savedDraft.rows.length > 0
      ? savedDraft.rows
      : [emptyPosRow(1)]
  );

  // Bottom summary fields
  const [extraDiscount, setExtraDiscount] = useState(savedDraft.extraDiscount || 0);

  // Modals
  const [showAddCustomerModal, setShowAddCustomerModal] = useState(false);
  const [showAddProductModal, setShowAddProductModal] = useState(false);
  const [newCustName, setNewCustName] = useState('');
  const [newCustPhone, setNewCustPhone] = useState('');
  const [newCustState, setNewCustState] = useState('');
  const [newCustCity, setNewCustCity] = useState('');
  const [newCustPincode, setNewCustPincode] = useState('');
  const [newCustGstin, setNewCustGstin] = useState('');

  const [newProdName, setNewProdName] = useState('');
  const [newProdPrice, setNewProdPrice] = useState('');
  const [newProdCost, setNewProdCost] = useState('');
  const [newProdAfter, setNewProdAfter] = useState('');
  const [newProdGst, setNewProdGst] = useState('5');
  const [newProdMode, setNewProdMode] = useState('before');

  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [settlementType, setSettlementType] = useState('full'); // full | half | partial | credit
  const [paymentMethod, setPaymentMethod] = useState('cash'); // cash | upi | bank
  const [amountPaidNow, setAmountPaidNow] = useState('');
  const [custOpen, setCustOpen] = useState(false);
  const [prodOpenIdx, setProdOpenIdx] = useState(null);
  const customerBoxRef = useRef(null);
  const tableContainerRef = useRef(null);

  useEffect(() => {
    fetchInitialData();
    const interval = setInterval(() => {
      setBillTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const onDocClick = (e) => {
      if (customerBoxRef.current && !customerBoxRef.current.contains(e.target)) {
        setCustOpen(false);
      }
      if (!e.target.closest('.pos-product-cell')) {
        setProdOpenIdx(null);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  const fetchInitialData = () => {
    getProducts().then((res) => setProducts(res.data.results || res.data)).catch(console.error);
    getCustomers().then((res) => {
      const list = res.data.results || res.data;
      setCustomers(list);
      const qName = searchParams.get('customer');
      const qPhone = searchParams.get('phone');
      if (qName) {
        setCustomerName(qName);
        const match = list.find((c) => c.name.toLowerCase() === qName.toLowerCase());
        setCustomerPhone(qPhone || match?.phone || '');
      }
    }).catch(console.error);
    getCompanySettings().then((res) => {
      const dataList = res.data.results || res.data;
      setCompanySettings(dataList[0] || null);
      if (dataList[0]?.gst_percentage != null) {
        setNewProdGst(normalizeGstRate(dataList[0].gst_percentage, 5));
      }
    }).catch(console.error);
  };

  useEffect(() => {
    writePosDraft({
      customerName,
      customerPhone,
      extraDiscount,
      billDate,
      rows,
    });
  }, [customerName, customerPhone, extraDiscount, billDate, rows]);

  const handleProductSelect = (index, productId) => {
    const selected = products.find((p) => String(p.id) === String(productId));
    const newRows = [...rows];
    if (selected) {
      const price = Number(selected.price);
      newRows[index] = {
        ...newRows[index],
        product_id: selected.id,
        product_name: selected.name,
        pack: selected.uom || '1 Unit',
        hsn: selected.hsn_code || '',
        gst_rate: Number(selected.gst_rate ?? companySettings?.gst_percentage ?? 0),
        mrp: price,
        rate: price,
        amount: price * newRows[index].qty - newRows[index].disc,
      };
    } else {
      newRows[index] = {
        ...newRows[index],
        product_id: '',
        product_name: '',
        mrp: 0,
        rate: 0,
        amount: 0,
      };
    }
    setRows(newRows);
  };

  const handleRowChange = (index, field, value) => {
    const newRows = [...rows];
    const valNum = Number(value) || 0;
    newRows[index][field] = valNum;

    const qty = field === 'qty' ? valNum : newRows[index].qty;
    const rate = field === 'rate' ? valNum : newRows[index].rate;
    const disc = field === 'disc' ? valNum : newRows[index].disc;
    if (field === 'gst_rate') newRows[index].gst_rate = valNum;

    newRows[index].amount = Math.max(0, qty * rate - disc);
    setRows(newRows);
  };

  const focusProductInput = (rowIndex) => {
    requestAnimationFrame(() => {
      const input = tableContainerRef.current?.querySelector(
        `tr[data-pos-row="${rowIndex}"] .pos-product-cell input`
      );
      if (input) {
        input.focus();
        input.select?.();
      }
    });
  };

  const handleAddRow = (focusNew = false) => {
    setRows((prev) => {
      const nextId = (prev.reduce((m, r) => Math.max(m, Number(r.id) || 0), 0) || 0) + 1;
      const next = [
        ...prev,
        emptyPosRow(nextId, companySettings?.gst_percentage ?? 0),
      ];
      if (focusNew) {
        const newIdx = next.length - 1;
        setTimeout(() => focusProductInput(newIdx), 0);
      }
      return next;
    });
  };

  const handleRemoveRow = (index) => {
    setRows((prev) => {
      if (prev.length <= 1) {
        return [emptyPosRow(1, companySettings?.gst_percentage ?? 0)];
      }
      return prev.filter((_, i) => i !== index);
    });
  };

  const handleClear = () => {
    setRows([emptyPosRow(1, companySettings?.gst_percentage ?? 0)]);
    setCustomerName('');
    setCustomerPhone('');
    setExtraDiscount(0);
    setSuccessMsg('');
    setShowPaymentModal(false);
    setSettlementType('full');
    setPaymentMethod('cash');
    setAmountPaidNow('');
    clearPosDraft();
  };

  const addRowRef = useRef(() => {});
  const modalBlockRef = useRef(false);
  addRowRef.current = () => handleAddRow(true);
  modalBlockRef.current = showPaymentModal || showAddCustomerModal || showAddProductModal;

  useEffect(() => {
    const onKeyDown = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      if (e.key !== 'Enter' && e.code !== 'Enter' && e.keyCode !== 13) return;
      const tag = (e.target?.tagName || '').toLowerCase();
      if (tag === 'textarea') return;
      if (modalBlockRef.current) return;
      e.preventDefault();
      e.stopPropagation();
      addRowRef.current();
    };
    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, []);

  const validItems = rows.filter((r) => r.product_id && r.qty > 0);
  const subtotal = validItems.reduce((sum, r) => sum + r.amount, 0);
  const totalItemsCount = validItems.reduce((sum, r) => sum + r.qty, 0);
  const companyGst = Number(companySettings?.gst_percentage || 0);
  const party = customers.find((c) => {
    const sameName = c.name.toLowerCase() === (customerName || '').trim().toLowerCase();
    if (!sameName) return false;
    if (!(customerPhone || '').trim()) return true;
    return (c.phone || '') === (customerPhone || '').trim();
  }) || customers.find((c) => c.name.toLowerCase() === (customerName || '').trim().toLowerCase());
  const interstate = saleIsInterstate({
    companyGstin: companySettings?.gstin,
    companyState: companySettings?.state,
    customerGstin: party?.gstin || '',
    customerState: party?.state || '',
  });
  const afterDiscount = Math.max(0, subtotal - Number(extraDiscount || 0));
  const discountRatio = subtotal > 0 ? afterDiscount / subtotal : 1;
  const money2 = (n) => Math.round((Number(n) || 0) * 100) / 100;
  const gstAmount = money2(validItems.reduce((sum, r) => {
    const rate = Number(r.gst_rate ?? companyGst) || 0;
    return sum + (r.amount * discountRatio * rate / 100);
  }, 0));
  const gstPct = afterDiscount > 0 ? (gstAmount / afterDiscount) * 100 : companyGst;
  const cgstAmount = interstate ? 0 : money2(gstAmount / 2);
  const sgstAmount = interstate ? 0 : money2(gstAmount - cgstAmount);
  const igstAmount = interstate ? gstAmount : 0;
  const finalTotal = afterDiscount + gstAmount;

  const collectedAmount = (() => {
    if (settlementType === 'full') return finalTotal;
    if (settlementType === 'half') return Math.round((finalTotal / 2) * 100) / 100;
    if (settlementType === 'credit') return 0;
    return Math.min(finalTotal, Math.max(0, Number(amountPaidNow) || 0));
  })();
  const balanceDue = Math.max(0, Math.round((finalTotal - collectedAmount) * 100) / 100);

  const openPaymentPopup = () => {
    if (validItems.length === 0) {
      toast.showError('Please add at least one product using Add row.');
      return;
    }
    setSettlementType('full');
    setPaymentMethod('cash');
    setAmountPaidNow(String(finalTotal.toFixed(2)));
    setShowPaymentModal(true);
  };

  const handleSaveAndPrint = (isEstimate = false, paymentOverride = null) => {
    if (validItems.length === 0) {
      toast.showError('Please add at least one product using Add row.');
      return;
    }

    let payment_type = 'full_payment';
    let amount_paid_now = finalTotal;
    let payment_method = 'cash';

    if (isEstimate) {
      payment_type = 'full_credit';
      amount_paid_now = 0;
    } else if (paymentOverride) {
      payment_type = paymentOverride.payment_type;
      amount_paid_now = paymentOverride.amount_paid_now;
      payment_method = paymentOverride.payment_method;
    }

    setLoading(true);
    const locBits = [party?.address, party?.city, party?.state, party?.pincode].filter(Boolean);
    const payload = {
      customer_name: customerName || 'Walk-in Customer',
      customer_phone: customerPhone,
      customer_address: locBits.join(', '),
      customer_state: party?.state || '',
      customer_gstin: (party?.gstin || '').trim().toUpperCase(),
      payment_type,
      amount_paid_now,
      payment_method,
      notes: isEstimate
        ? 'Estimate Bill'
        : `POS sale · ${payment_type === 'full_credit' ? 'CREDIT' : String(payment_method).toUpperCase()} · ${payment_type.replace('_', ' ')}`,
      items: validItems.map((r) => ({
        product_id: r.product_id,
        quantity: r.qty,
        unit_price: r.rate,
        discount: r.disc || 0,
        gst_rate: r.gst_rate,
      })),
    };

    createInvoicePos(payload)
      .then((res) => {
        setLoading(false);
        const inv = res.data.invoice;
        const msg = `Bill #${inv.invoice_number} saved successfully! Total: ₹${inv.total_amount}`;
        toast.showSuccess(msg);
        if (!isEstimate) {
          window.open(`/billing/invoices/${inv.id}/print/`, '_blank');
        }
        setRows([emptyPosRow(1, companySettings?.gst_percentage ?? 0)]);
        setCustomerName('');
        setCustomerPhone('');
        setExtraDiscount(0);
        setShowPaymentModal(false);
        setSettlementType('full');
        setPaymentMethod('cash');
        setAmountPaidNow('');
        clearPosDraft();
        setSuccessMsg(msg);
      })
      .catch((err) => {
        setLoading(false);
        console.error(err);
        toast.showError(err.response?.data?.error || 'Failed to save bill.');
      });
  };

  const confirmPaymentAndPrint = () => {
    if (settlementType === 'credit' && !customerName.trim()) {
      toast.showError('Enter customer name for credit / later payment.');
      return;
    }
    if (settlementType === 'partial' && collectedAmount <= 0) {
      toast.showError('Enter the amount collected now, or choose Full Credit.');
      return;
    }
    if (settlementType !== 'credit' && collectedAmount <= 0) {
      toast.showError('Amount collected must be greater than 0, or choose Credit.');
      return;
    }

    let payment_type = 'full_payment';
    if (settlementType === 'credit' || collectedAmount <= 0) {
      payment_type = 'full_credit';
    } else if (collectedAmount + 0.001 < finalTotal) {
      payment_type = 'partial_credit';
    }

    handleSaveAndPrint(false, {
      payment_type,
      amount_paid_now: collectedAmount,
      payment_method: settlementType === 'credit' ? 'other' : (paymentMethod === 'bank' ? 'bank_transfer' : paymentMethod),
    });
  };

  const handleCreateCustomerSubmit = (e) => {
    e.preventDefault();
    if (!newCustName.trim()) {
      toast.showError('Customer name is required.');
      return;
    }
    if (!newCustState.trim()) {
      toast.showError('State is required.');
      return;
    }
    createCustomer({
      name: newCustName.trim(),
      phone: newCustPhone.trim(),
      state: newCustState.trim(),
      city: newCustCity.trim(),
      pincode: newCustPincode.trim(),
      gstin: newCustGstin.trim().toUpperCase(),
    })
      .then((res) => {
        setCustomers([...customers, res.data]);
        setCustomerName(res.data.name);
        setCustomerPhone(res.data.phone || '');
        setShowAddCustomerModal(false);
        setNewCustName('');
        setNewCustPhone('');
        setNewCustState('');
        setNewCustCity('');
        setNewCustPincode('');
        setNewCustGstin('');
        setCustOpen(false);
        toast.showSuccess(`Customer '${res.data.name}' added.`);
      })
      .catch((err) => {
        const data = err.response?.data;
        const msg = data?.gstin?.[0] || data?.state?.[0] || data?.name?.[0] || data?.phone?.[0] || data?.detail || data?.error || 'Failed to add customer.';
        toast.showError(typeof msg === 'string' ? msg : 'Failed to add customer.');
      });
  };

  const openAddCustomer = (nameHint = customerName) => {
    setNewCustName((nameHint || '').trim());
    setNewCustPhone(customerPhone || '');
    setNewCustState('');
    setNewCustCity('');
    setNewCustPincode('');
    setNewCustGstin('');
    setShowAddCustomerModal(true);
    setCustOpen(false);
  };

  const selectCustomer = (cust) => {
    if (!cust) {
      setCustomerName('');
      setCustomerPhone('');
    } else {
      setCustomerName(cust.name);
      setCustomerPhone(cust.phone || '');
    }
    setCustOpen(false);
  };

  const customerQuery = customerName.trim().toLowerCase();
  const filteredCustomers = customers.filter((c) => {
    if (!customerQuery) return true;
    return (
      c.name.toLowerCase().includes(customerQuery) ||
      (c.phone && c.phone.includes(customerQuery))
    );
  });
  const customerExists = customers.some((c) => c.name.toLowerCase() === customerQuery);

  const handleCreateProductSubmit = (e) => {
    e.preventDefault();
    const gst = Number(newProdGst);
    const math = newProdMode === 'after'
      ? beforeFromInclusive(newProdAfter, gst)
      : sellingGstMath(newProdPrice, gst);
    createProduct({
      name: newProdName,
      price: math.before,
      cost_price: Number(newProdCost || math.before),
      gst_rate: gst,
      price_mode: 'before',
    }).then((res) => {
      setProducts([...products, res.data]);
      setShowAddProductModal(false);
      setNewProdName('');
      setNewProdPrice('');
      setNewProdCost('');
      setNewProdAfter('');
      setNewProdMode('before');
    });
  };

  return (
    <div className="pos-container-image1">
      {rows.some((r) => r.product_id) && (
        <div style={{ backgroundColor: '#FFFBEB', border: '1px solid #FDE68A', padding: '8px 14px', borderRadius: '8px', color: '#92400E', fontWeight: '600', fontSize: '0.8rem' }}>
          Draft saved — leave this page and come back; this bill stays as you left it. Clear bill to start fresh.
        </div>
      )}
      {successMsg && (
        <div style={{ backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0', padding: '12px 16px', borderRadius: '8px', color: '#065F46', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle size={18} />
          {successMsg}
        </div>
      )}

      {/* Top Header Bar from Image 1 */}
      <div className="pos-header-inputs">
        {/* Customer Search / Type */}
        <div className="pos-field-box" style={{ flex: '1 1 260px' }} ref={customerBoxRef}>
          <span className="pos-field-label">CUSTOMER / WALK-IN</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <User size={16} color="#64748B" />
            <input
              type="text"
              placeholder="Search or type name..."
              className="pos-input-text"
              value={customerName}
              autoComplete="off"
              onFocus={() => setCustOpen(true)}
              onChange={(e) => {
                setCustomerName(e.target.value);
                setCustOpen(true);
                const match = customers.find((c) => c.name.toLowerCase() === e.target.value.toLowerCase());
                if (match) setCustomerPhone(match.phone || '');
              }}
            />
            <button
              type="button"
              onClick={() => setCustOpen((open) => !open)}
              style={{ border: 'none', background: 'none', cursor: 'pointer', padding: 0, color: '#334155' }}
              aria-label="Open customer list"
            >
              <ChevronDown size={16} />
            </button>
          </div>
          {custOpen && (
            <div className="pos-search-menu">
              <button type="button" className="pos-search-option" onClick={() => selectCustomer(null)}>
                <span>Walk-in Customer</span>
                <span style={{ color: '#94A3B8', fontSize: '0.75rem' }}>No ledger</span>
              </button>
              {filteredCustomers.map((c) => (
                <button key={c.id} type="button" className="pos-search-option" onClick={() => selectCustomer(c)}>
                  <span style={{ fontWeight: 700 }}>{c.name}</span>
                  <span style={{ color: '#64748B', fontSize: '0.75rem' }}>{c.phone || ''}</span>
                </button>
              ))}
              {filteredCustomers.length === 0 && customerQuery && (
                <div style={{ padding: '10px 12px', fontSize: '0.8rem', color: '#94A3B8' }}>No matching customer</div>
              )}
              {customerQuery && !customerExists && (
                <button type="button" className="pos-search-option add-new" onClick={() => openAddCustomer(customerName)}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <UserPlus size={14} /> Add customer “{customerName.trim()}”
                  </span>
                </button>
              )}
              {!customerQuery && (
                <button type="button" className="pos-search-option add-new" onClick={() => openAddCustomer('')}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <UserPlus size={14} /> Add new customer
                  </span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Phone */}
        <div className="pos-field-box" style={{ width: '150px' }}>
          <span className="pos-field-label">PHONE</span>
          <input
            type="text"
            placeholder="PHONE"
            className="pos-input-text"
            value={customerPhone}
            onChange={(e) => setCustomerPhone(e.target.value)}
          />
        </div>

        {/* Bill # */}
        <div className="pos-field-box green-box" style={{ width: '130px' }}>
          <span className="pos-field-label">BILL #</span>
          <input
            type="text"
            className="pos-input-text"
            style={{ fontWeight: '700', color: '#0F766E' }}
            value={billNumber}
            onChange={(e) => setBillNumber(e.target.value)}
          />
        </div>

        {/* Date */}
        <div className="pos-field-box green-box" style={{ width: '150px' }}>
          <span className="pos-field-label">DATE</span>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <input
              type="date"
              className="pos-input-text"
              style={{ fontWeight: '600', fontSize: '0.85rem' }}
              value={billDate}
              onChange={(e) => setBillDate(e.target.value)}
            />
          </div>
        </div>

        {/* Time */}
        <div className="pos-field-box green-box" style={{ width: '130px' }}>
          <span className="pos-field-label">TIME</span>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: '700', fontSize: '0.85rem', color: '#0F766E' }}>{billTime}</span>
            <Clock size={14} color="#0F766E" />
          </div>
        </div>

        {/* + Product Button */}
        <button
          type="button"
          onClick={() => setShowAddProductModal(true)}
          className="btn-smart btn-primary-smart"
          style={{ backgroundColor: '#059669', borderRadius: '8px', height: '44px', marginLeft: 'auto' }}
        >
          <Plus size={16} /> New Product
        </button>
      </div>

      {/* POS Table replicating Image 1 */}
      <div className="pos-table-container" ref={tableContainerRef}>
        <div className="pos-table-scroll">
        <table className="pos-table-img1">
          <thead>
            <tr>
              <th style={{ width: '40px', textAlign: 'center' }}>#</th>
              <th style={{ width: '280px' }}>PRODUCT</th>
              <th>MRP</th>
              <th>QTY</th>
              <th>LOOSE</th>
              <th>DISC</th>
              <th>RATE</th>
              <th>GST %</th>
              <th style={{ textAlign: 'right' }}>AMOUNT</th>
              <th style={{ width: '40px' }}></th>
            </tr>
          </thead>
          <tbody>
              {rows.map((row, idx) => (
                <tr key={row.id} data-pos-row={idx}>
                <td style={{ textAlign: 'center', fontWeight: '700', color: '#64748B' }}>{idx + 1}</td>
                <td style={{ position: 'relative', overflow: 'visible' }}>
                  <div className="pos-product-cell" style={{ position: 'relative' }}>
                    <input
                      type="text"
                      placeholder="Search SKU or Product Name..."
                      className="pos-table-input"
                      value={row.product_name}
                      autoComplete="off"
                      onFocus={() => setProdOpenIdx(idx)}
                      onChange={(e) => {
                        const val = e.target.value;
                        setProdOpenIdx(idx);
                        const matched = products.find(
                          (p) =>
                            p.name.toLowerCase() === val.toLowerCase() ||
                            (p.sku && p.sku.toLowerCase() === val.toLowerCase()) ||
                            `${p.name}${p.sku ? ` (${p.sku})` : ''}`.toLowerCase() === val.toLowerCase()
                        );
                        if (matched) {
                          handleProductSelect(idx, matched.id);
                        } else {
                          const newRows = [...rows];
                          newRows[idx].product_name = val;
                          newRows[idx].product_id = '';
                          setRows(newRows);
                        }
                      }}
                      style={{ fontWeight: '600', paddingRight: '22px' }}
                    />
                    <button
                      type="button"
                      onClick={() => setProdOpenIdx(prodOpenIdx === idx ? null : idx)}
                      style={{ position: 'absolute', right: 4, top: '50%', transform: 'translateY(-50%)', border: 'none', background: 'none', cursor: 'pointer', color: '#334155' }}
                    >
                      <ChevronDown size={14} />
                    </button>
                    {prodOpenIdx === idx && (
                      <div className="pos-search-menu" style={{ minWidth: '280px' }}>
                        {products
                          .filter((p) => {
                            const q = (row.product_name || '').toLowerCase();
                            if (!q) return true;
                            return (
                              p.name.toLowerCase().includes(q) ||
                              (p.sku && p.sku.toLowerCase().includes(q))
                            );
                          })
                          .slice(0, 40)
                          .map((p) => (
                            <button
                              key={p.id}
                              type="button"
                              className="pos-search-option"
                              onClick={() => {
                                handleProductSelect(idx, p.id);
                                setProdOpenIdx(null);
                              }}
                            >
                              <span style={{ fontWeight: 700 }}>{p.name}{p.sku ? ` (${p.sku})` : ''}</span>
                              <span style={{ color: '#047857', fontWeight: 700 }}>₹{Number(p.selling_price_after_gst ?? p.price).toFixed(2)}</span>
                            </button>
                          ))}
                        {products.filter((p) => {
                          const q = (row.product_name || '').toLowerCase();
                          if (!q) return true;
                          return p.name.toLowerCase().includes(q) || (p.sku && p.sku.toLowerCase().includes(q));
                        }).length === 0 && (
                          <div style={{ padding: '10px 12px', fontSize: '0.8rem', color: '#94A3B8' }}>No matching product</div>
                        )}
                      </div>
                    )}
                  </div>
                </td>
                <td>
                  <input type="number" className="pos-table-input" value={row.mrp} readOnly style={{ backgroundColor: '#F8FAFC' }} />
                </td>
                <td>
                  <input
                    type="number"
                    min="1"
                    className="pos-table-input"
                    value={row.qty}
                    onChange={(e) => handleRowChange(idx, 'qty', e.target.value)}
                    style={{ fontWeight: '700', textAlign: 'center' }}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    className="pos-table-input"
                    value={row.loose}
                    onChange={(e) => handleRowChange(idx, 'loose', e.target.value)}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    className="pos-table-input"
                    value={row.disc}
                    onChange={(e) => handleRowChange(idx, 'disc', e.target.value)}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    className="pos-table-input"
                    value={row.rate}
                    onChange={(e) => handleRowChange(idx, 'rate', e.target.value)}
                    style={{ fontWeight: '600' }}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    className="pos-table-input"
                    value={row.gst_rate ?? ''}
                    onChange={(e) => handleRowChange(idx, 'gst_rate', e.target.value)}
                    style={{ fontWeight: '800', textAlign: 'center', backgroundColor: '#F0FDFA', color: '#0F766E' }}
                  />
                </td>
                <td style={{ textAlign: 'right', fontWeight: '800', color: '#0F172A' }}>
                  ₹{row.amount.toFixed(2)}
                </td>
                <td style={{ textAlign: 'center' }}>
                    <button
                      type="button"
                      onClick={() => handleRemoveRow(idx)}
                      style={{ border: 'none', background: 'none', color: '#DC2626', cursor: 'pointer' }}
                    >
                      <Trash2 size={16} />
                    </button>
                </td>
              </tr>
              ))}
          </tbody>
        </table>
        </div>

        {/* Hint bar in Image 1 */}
        <div className="hint-bar">
          Search product in the table — GST % is editable per line · Ctrl+Enter: new row · Tab: Qty → Loose → Disc → Rate → GST
        </div>
      </div>

      {/* Footer docked to bottom — more room for many item rows above */}
      <div className="pos-footer-dock">
      {/* Row add button bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          type="button"
          onClick={() => handleAddRow(true)}
          className="btn-smart btn-outline-smart"
          style={{ borderColor: '#059669', color: '#047857', fontWeight: '700' }}
        >
          <Plus size={16} /> Add row
        </button>
        <span style={{ fontSize: '0.8rem', color: '#64748B' }}>Ctrl+Enter — add new row · Tab: Qty → Loose → Disc → Rate</span>
      </div>

      {/* Bottom Summary Bar from Image 1 */}
      <div className="pos-summary-bar">
        <div className="summary-pills-group">
          {/* Discount Pill */}
          <div className="pos-field-box" style={{ width: '130px', minHeight: '44px', borderRadius: '20px' }}>
            <span className="pos-field-label" style={{ borderRadius: '4px' }}>DISCOUNT ₹</span>
            <input
              type="number"
              placeholder="0"
              className="pos-input-text"
              style={{ textAlign: 'center', fontWeight: '700' }}
              value={extraDiscount}
              onChange={(e) => setExtraDiscount(e.target.value)}
            />
          </div>

          {/* Items Pill */}
          <div className="pill-card">
            <div className="pill-card-label">Items</div>
            <div className="pill-card-val">{totalItemsCount}</div>
          </div>

          {/* Subtotal Pill */}
          <div className="pill-card">
            <div className="pill-card-label">Subtotal</div>
            <div className="pill-card-val">₹{subtotal.toFixed(2)}</div>
          </div>
          {interstate ? (
            <div className="pill-card">
              <div className="pill-card-label">IGST {gstPct.toFixed(2)}%</div>
              <div className="pill-card-val">₹{igstAmount.toFixed(2)}</div>
            </div>
          ) : (
            <>
              <div className="pill-card">
                <div className="pill-card-label">CGST {(gstPct / 2).toFixed(2)}%</div>
                <div className="pill-card-val">₹{cgstAmount.toFixed(2)}</div>
              </div>
              <div className="pill-card">
                <div className="pill-card-label">SGST {(gstPct / 2).toFixed(2)}%</div>
                <div className="pill-card-val">₹{sgstAmount.toFixed(2)}</div>
              </div>
            </>
          )}

          {/* TOTAL Pill Box (Image 1 Style) */}
          <div className="total-pill-box">
            <div className="pill-card-label">TOTAL</div>
            <div className="pill-card-val">₹{finalTotal.toFixed(2)}</div>
          </div>
        </div>

        {/* Action Buttons from Image 1 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            disabled={loading}
            onClick={() => handleSaveAndPrint(true)}
            className="btn-smart btn-outline-smart"
            style={{ borderRadius: '8px' }}
          >
            <FileText size={16} /> Estimate Bill
          </button>

          <button
            type="button"
            disabled={loading}
            onClick={openPaymentPopup}
            className="btn-smart btn-primary-smart"
            style={{ backgroundColor: '#059669', borderRadius: '8px', padding: '10px 20px' }}
          >
            <Printer size={16} /> Save and Print
          </button>

          <button
            type="button"
            onClick={handleClear}
            className="btn-smart btn-outline-smart"
            style={{ borderRadius: '8px' }}
          >
            <RotateCcw size={16} /> Clear
          </button>
        </div>
      </div>
      </div>

      {/* Add Customer Modal */}
      {showAddCustomerModal && (
        <div className="modal-backdrop" onClick={() => setShowAddCustomerModal(false)}>
          <div className="modal-content-smart" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontWeight: '700', marginBottom: '16px' }}>Add Customer</h3>
            <form onSubmit={handleCreateCustomerSubmit}>
              <div className="form-field">
                <label className="form-field-label" htmlFor="pos-cust-name">Customer Name *</label>
                <input
                  id="pos-cust-name"
                  type="text"
                  className="form-control-smart"
                  required
                  placeholder="Full name or business name"
                  value={newCustName}
                  onChange={(e) => setNewCustName(e.target.value)}
                />
              </div>
              <div className="form-field">
                <label className="form-field-label" htmlFor="pos-cust-phone">Phone</label>
                <input
                  id="pos-cust-phone"
                  type="text"
                  className="form-control-smart"
                  placeholder="10-digit mobile number"
                  maxLength={10}
                  value={newCustPhone}
                  onChange={(e) => setNewCustPhone(e.target.value)}
                />
              </div>
              <div className="form-field">
                <label className="form-field-label" htmlFor="pos-cust-gstin">GST No (optional)</label>
                <input
                  id="pos-cust-gstin"
                  type="text"
                  className="form-control-smart"
                  placeholder="15-character GSTIN e.g. 06ABCDE1234F1Z5"
                  maxLength={15}
                  value={newCustGstin}
                  onChange={(e) => setNewCustGstin(e.target.value.toUpperCase())}
                  style={{ textTransform: 'uppercase' }}
                />
              </div>
              <div className="form-field">
                <label className="form-field-label" htmlFor="pos-cust-state">State *</label>
                <select
                  id="pos-cust-state"
                  className="form-control-smart"
                  required
                  value={newCustState}
                  onChange={(e) => setNewCustState(e.target.value)}
                >
                  <option value="">Select state</option>
                  {INDIAN_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div className="form-field" style={{ marginBottom: 0 }}>
                  <label className="form-field-label" htmlFor="pos-cust-city">City</label>
                  <input id="pos-cust-city" type="text" className="form-control-smart" placeholder="City" value={newCustCity} onChange={(e) => setNewCustCity(e.target.value)} />
                </div>
                <div className="form-field" style={{ marginBottom: 0 }}>
                  <label className="form-field-label" htmlFor="pos-cust-pincode">Pincode</label>
                  <input id="pos-cust-pincode" type="text" className="form-control-smart" placeholder="6-digit pincode" maxLength={6} value={newCustPincode} onChange={(e) => setNewCustPincode(e.target.value)} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: 8 }}>
                <button type="button" className="btn-smart btn-secondary-smart" onClick={() => setShowAddCustomerModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#0D9488' }}>
                  Save Customer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Product Modal */}
      {showAddProductModal && (
        <div className="modal-backdrop">
          <div className="modal-content-smart">
            <h3 style={{ fontWeight: '700', marginBottom: '16px' }}>Add Quick Product Item</h3>
            <form onSubmit={handleCreateProductSubmit}>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: '600', color: '#64748B', display: 'block', marginBottom: '4px' }}>Item Name</label>
                <input type="text" className="form-control-smart" required value={newProdName} onChange={(e) => setNewProdName(e.target.value)} />
              </div>
              <PricingGstCard
                settings={companySettings}
                costPrice={newProdCost}
                sellingBefore={newProdPrice}
                sellingAfter={newProdAfter}
                gstRate={newProdGst}
                priceMode={newProdMode}
                onChange={(next) => {
                  setNewProdCost(next.costPrice);
                  setNewProdPrice(next.sellingBefore);
                  setNewProdAfter(next.sellingAfter);
                  setNewProdGst(next.gstRate);
                  setNewProdMode(next.priceMode);
                }}
              />
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: 16 }}>
                <button type="button" className="btn-smart btn-secondary-smart" onClick={() => setShowAddProductModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#0D9488' }}>
                  Save Item
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showPaymentModal && (
        <div className="modal-backdrop" onClick={() => !loading && setShowPaymentModal(false)}>
          <div className="modal-content-smart" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontWeight: '800', color: '#0F172A', fontSize: '1.2rem' }}>Collect Payment</h3>
                <p style={{ fontSize: '0.8rem', color: '#64748B', marginTop: '4px' }}>
                  {customerName || 'Walk-in Customer'} {customerPhone ? `· ${customerPhone}` : ''}
                </p>
              </div>
              <button type="button" onClick={() => setShowPaymentModal(false)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#64748B' }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '16px' }}>
              <div style={{ padding: '12px', background: '#F8FAFC', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#64748B', textTransform: 'uppercase' }}>Bill total</div>
                <div style={{ fontSize: '1.35rem', fontWeight: '900', color: '#0F172A' }}>₹{finalTotal.toFixed(2)}</div>
                {gstAmount > 0 && (
                  <div style={{ fontSize: '0.7rem', color: '#64748B' }}>
                    {interstate
                      ? `Inter-state IGST ₹${igstAmount.toFixed(2)} (${gstPct.toFixed(2)}%)`
                      : `Intra-state CGST ₹${cgstAmount.toFixed(2)} + SGST ₹${sgstAmount.toFixed(2)} (${(gstPct / 2).toFixed(2)}% + ${(gstPct / 2).toFixed(2)}%)`}
                  </div>
                )}
              </div>
              <div style={{ padding: '12px', background: balanceDue > 0 ? '#FEF3C7' : '#ECFDF5', borderRadius: '10px', border: `1px solid ${balanceDue > 0 ? '#FCD34D' : '#A7F3D0'}` }}>
                <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#64748B', textTransform: 'uppercase' }}>Balance due</div>
                <div style={{ fontSize: '1.35rem', fontWeight: '900', color: balanceDue > 0 ? '#B45309' : '#047857' }}>₹{balanceDue.toFixed(2)}</div>
              </div>
            </div>

            <div style={{ fontSize: '0.75rem', fontWeight: '800', color: '#64748B', letterSpacing: '0.04em', marginBottom: '8px' }}>SETTLEMENT</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '16px' }}>
              {[
                { id: 'full', label: 'Full payment' },
                { id: 'half', label: 'Half payment' },
                { id: 'partial', label: 'Partial / custom' },
                { id: 'credit', label: 'Full credit' },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => {
                    setSettlementType(opt.id);
                    if (opt.id === 'full') setAmountPaidNow(finalTotal.toFixed(2));
                    if (opt.id === 'half') setAmountPaidNow((Math.round((finalTotal / 2) * 100) / 100).toFixed(2));
                    if (opt.id === 'credit') setAmountPaidNow('0');
                    if (opt.id === 'partial') setAmountPaidNow(amountPaidNow || '');
                  }}
                  className="btn-smart"
                  style={{
                    justifyContent: 'center',
                    border: settlementType === opt.id ? '2px solid #059669' : '1px solid #E2E8F0',
                    backgroundColor: settlementType === opt.id ? '#ECFDF5' : '#FFFFFF',
                    color: settlementType === opt.id ? '#047857' : '#334155',
                    fontWeight: '700',
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {settlementType !== 'credit' && (
              <>
                <div style={{ fontSize: '0.75rem', fontWeight: '800', color: '#64748B', letterSpacing: '0.04em', marginBottom: '8px' }}>PAYMENT MODE</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '8px', marginBottom: '16px' }}>
                  {[
                    { id: 'cash', label: 'Cash', icon: Banknote },
                    { id: 'upi', label: 'UPI', icon: Smartphone },
                    { id: 'bank', label: 'Bank', icon: Landmark },
                    { id: 'other', label: 'Other', icon: FileText },
                  ].map((opt) => {
                    const Icon = opt.icon;
                    const st = paymentModeStyle(opt.id);
                    const on = paymentMethod === opt.id;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => setPaymentMethod(opt.id)}
                        className="btn-smart"
                        style={{
                          justifyContent: 'center',
                          flexDirection: 'column',
                          height: '64px',
                          gap: '4px',
                          border: on ? `2px solid ${st.color}` : `1px solid ${st.border}`,
                          backgroundColor: st.bg,
                          color: st.color,
                          fontWeight: '800',
                        }}
                      >
                        <Icon size={18} />
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </>
            )}

            <div style={{ marginBottom: '16px' }}>
              <label className="pos-field-label">AMOUNT COLLECTED NOW (₹)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max={finalTotal}
                className="form-control-smart"
                disabled={settlementType === 'full' || settlementType === 'half' || settlementType === 'credit'}
                value={settlementType === 'partial' ? amountPaidNow : collectedAmount.toFixed(2)}
                onChange={(e) => setAmountPaidNow(e.target.value)}
                style={{ fontSize: '1.15rem', fontWeight: '800' }}
              />
              {settlementType === 'partial' && (
                <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '6px' }}>
                  Remaining credit: ₹{balanceDue.toFixed(2)}
                </div>
              )}
              {settlementType === 'credit' && (
                <div style={{ fontSize: '0.75rem', color: '#B45309', marginTop: '6px' }}>
                  Entire bill goes to customer ledger as outstanding.
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button type="button" className="btn-smart btn-outline-smart" disabled={loading} onClick={() => setShowPaymentModal(false)}>
                Back
              </button>
              <button
                type="button"
                className="btn-smart btn-primary-smart"
                disabled={loading}
                onClick={confirmPaymentAndPrint}
                style={{ backgroundColor: '#059669' }}
              >
                <Printer size={16} />
                {loading ? 'Saving...' : 'Confirm & Print'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
