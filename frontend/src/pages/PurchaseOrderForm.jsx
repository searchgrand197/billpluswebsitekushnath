import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  getPurchaseOrder, createPurchaseOrder, updatePurchaseOrder,
  getSuppliers, createSupplier, getRawMaterials, getCompanySettings,
} from '../api';
import { Plus, Trash2, Save, Send } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import { allowedGstRates, PAYMENT_TERMS, money, normalizeGstRate, saleIsInterstate } from './poUtils';

const emptyLine = (gst = '0') => ({
  raw_material: '', hsn_code: '', specification: '', quantity: '1', uom: 'kg',
  unit_cost: '0', discount: '0', gst_rate: String(gst),
});

function lineMath(line, interstate) {
  const qty = Number(line.quantity) || 0;
  const rate = Number(line.unit_cost) || 0;
  const disc = Number(line.discount) || 0;
  const gstPct = Number(line.gst_rate) || 0;
  const basic = qty * rate;
  const taxable = Math.max(0, basic - disc);
  const gst = taxable * gstPct / 100;
  const cgst = interstate ? 0 : gst / 2;
  const sgst = interstate ? 0 : gst / 2;
  const igst = interstate ? gst : 0;
  return { basic, taxable, cgst, sgst, igst, total: taxable + cgst + sgst + igst };
}

export default function PurchaseOrderForm() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const toast = useToast();
  const [suppliers, setSuppliers] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showSupplier, setShowSupplier] = useState(false);
  const [supplierId, setSupplierId] = useState('');
  const [header, setHeader] = useState({
    order_date: new Date().toISOString().slice(0, 10),
    expected_delivery_date: '',
    warehouse: '',
    payment_terms: '30',
    payment_due_date: '',
    payment_notes: '',
    reference_number: '',
    delivery_address: '',
    transporter: '',
    vehicle_number: '',
    lr_number: '',
    delivery_instructions: '',
    notes: '',
    round_off: '0',
  });
  const [lines, setLines] = useState([emptyLine('0')]);
  const [charges, setCharges] = useState([{ name: 'Freight', amount: '', gst_applicable: false, gst_rate: '0' }]);
  const [newSup, setNewSup] = useState({ name: '', gstin: '', phone: '', address: '', state: '', contact_person: '' });

  useEffect(() => {
    getSuppliers().then((r) => setSuppliers(r.data.results || r.data));
    getRawMaterials().then((r) => setMaterials(r.data.results || r.data));
    getCompanySettings().then((r) => {
      const list = r.data.results || r.data;
      setSettings(list[0] || null);
    });
    if (id) {
      getPurchaseOrder(id).then((r) => {
        const po = r.data;
        setSupplierId(po.supplier ? String(po.supplier) : '');
        setHeader((h) => ({
          ...h,
          order_date: po.order_date,
          expected_delivery_date: po.expected_delivery_date || '',
          warehouse: po.warehouse || '',
          payment_terms: po.payment_terms || '30',
          payment_due_date: po.payment_due_date || '',
          payment_notes: po.payment_notes || '',
          reference_number: po.reference_number || '',
          delivery_address: po.delivery_address || '',
          transporter: po.transporter || '',
          vehicle_number: po.vehicle_number || '',
          lr_number: po.lr_number || '',
          delivery_instructions: po.delivery_instructions || '',
          notes: po.notes || '',
          round_off: String(po.round_off || 0),
        }));
        setLines((po.items || []).map((i) => ({
          raw_material: String(i.raw_material || ''),
          hsn_code: i.hsn_code || '',
          specification: i.specification || '',
          quantity: String(i.quantity),
          uom: i.uom,
          unit_cost: String(i.unit_cost),
          discount: String(i.discount || 0),
          gst_rate: normalizeGstRate(i.gst_rate, 0),
        })));
        setCharges(po.extra_charges?.length ? po.extra_charges.map((c) => ({
          name: c.name, amount: c.amount, gst_applicable: !!c.gst_applicable, gst_rate: c.gst_rate || '18',
        })) : [{ name: 'Freight', amount: '', gst_applicable: false, gst_rate: '18' }]);
      });
    }
  }, [id]);

  const defaultGst = normalizeGstRate(settings?.gst_percentage, 0);
  const gstOptions = allowedGstRates(settings);

  useEffect(() => {
    if (!settings || isEdit) return;
    setLines((ls) => ls.map((l) => (l.raw_material ? l : { ...l, gst_rate: defaultGst })));
    setCharges((cs) => cs.map((c) => (c.gst_rate === '0' || c.gst_rate === '18' ? { ...c, gst_rate: defaultGst } : c)));
  }, [defaultGst, isEdit, settings]);
  const supplier = suppliers.find((s) => String(s.id) === String(supplierId));
  const interstate = saleIsInterstate({
    companyGstin: settings?.gstin,
    companyState: settings?.state,
    customerGstin: supplier?.gstin,
    customerState: supplier?.state,
  });

  const preview = useMemo(() => {
    let subtotal = 0, discount = 0, taxable = 0, cgst = 0, sgst = 0, igst = 0;
    const rowCalcs = lines.map((ln) => {
      const m = lineMath(ln, interstate);
      subtotal += m.basic;
      discount += Number(ln.discount) || 0;
      taxable += m.taxable;
      cgst += m.cgst;
      sgst += m.sgst;
      igst += m.igst;
      return m;
    });
    let other = 0, ocgst = 0, osgst = 0, oigst = 0;
    charges.forEach((ch) => {
      const amt = Number(ch.amount) || 0;
      other += amt;
      if (ch.gst_applicable && amt) {
        const g = amt * (Number(ch.gst_rate) || 0) / 100;
        if (interstate) oigst += g;
        else { ocgst += g / 2; osgst += g / 2; }
      }
    });
    const round = Number(header.round_off) || 0;
    const grand = taxable + cgst + sgst + igst + other + ocgst + osgst + oigst + round;
    return { rowCalcs, subtotal, discount, taxable, cgst: cgst + ocgst, sgst: sgst + osgst, igst: igst + oigst, other, round, grand };
  }, [lines, charges, interstate, header.round_off]);

  const setLine = (idx, field, value) => {
    const next = [...lines];
    next[idx][field] = value;
    if (field === 'raw_material') {
      const rm = materials.find((m) => String(m.id) === String(value));
      if (rm) {
        next[idx].uom = rm.unit || 'kg';
        next[idx].unit_cost = String(rm.purchase_price || 0);
        next[idx].hsn_code = rm.hsn_code || '';
        next[idx].gst_rate = normalizeGstRate(rm.gst_rate, defaultGst);
      }
    }
    setLines(next);
  };

  const payload = (place) => ({
    supplier: supplierId || null,
    supplier_name: supplier?.name || '',
    supplier_phone: supplier?.phone || '',
    supplier_address: supplier?.address || '',
    supplier_gstin: supplier?.gstin || '',
    ...header,
    expected_delivery_date: header.expected_delivery_date || null,
    payment_due_date: header.payment_due_date || null,
    round_off: Number(header.round_off) || 0,
    extra_charges: charges.filter((c) => c.name && Number(c.amount) > 0),
    items: lines.filter((l) => l.raw_material && Number(l.quantity) > 0),
    place_order: !!place,
  });

  const save = (place) => {
    if (!supplierId) {
      toast.showError('Please select a supplier.');
      return;
    }
    if (!payload(false).items.length) {
      toast.showError('Add at least one raw material with quantity > 0.');
      return;
    }
    setSaving(true);
    const req = isEdit ? updatePurchaseOrder(id, payload(place)) : createPurchaseOrder(payload(place));
    req.then((res) => {
      toast.showSuccess(place ? 'Purchase Order placed with supplier.' : 'Purchase Order saved.');
      navigate(`/purchase-orders/${res.data.id}`);
    }).catch((e) => {
      toast.showError(e.response?.data?.error || 'Could not save purchase order.');
    }).finally(() => setSaving(false));
  };

  const addSupplier = (e) => {
    e.preventDefault();
    if (!newSup.name.trim()) {
      toast.showError('Supplier name is required.');
      return;
    }
    createSupplier(newSup).then((res) => {
      setSuppliers((prev) => [...prev, res.data]);
      setSupplierId(String(res.data.id));
      setShowSupplier(false);
      toast.showSuccess('Supplier added.');
    }).catch((err) => toast.showError(err.response?.data?.gstin?.[0] || 'Could not add supplier.'));
  };

  return (
    <div>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 6 }}>{isEdit ? 'Edit Purchase Order' : 'Create Purchase Order'}</h1>
      <p style={{ color: '#64748B', fontSize: '0.85rem', marginBottom: 16 }}>GST is recalculated on the server. Creating a PO does not increase stock.</p>

      <div className="smart-card" style={{ padding: 20, marginBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
          <div>
            <label className="pos-field-label">Supplier *</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <select className="form-control-smart" value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
                <option value="">Select supplier...</option>
                {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name} {s.gstin ? `(${s.gstin})` : ''}</option>)}
              </select>
              <button type="button" className="btn-smart btn-outline-smart" onClick={() => setShowSupplier(true)}><Plus size={14} /></button>
            </div>
          </div>
          <div>
            <label className="pos-field-label">PO Date *</label>
            <input type="date" className="form-control-smart" value={header.order_date} onChange={(e) => setHeader({ ...header, order_date: e.target.value })} />
          </div>
          <div>
            <label className="pos-field-label">Expected delivery</label>
            <input type="date" className="form-control-smart" value={header.expected_delivery_date} onChange={(e) => setHeader({ ...header, expected_delivery_date: e.target.value })} />
          </div>
          <div>
            <label className="pos-field-label">Payment terms</label>
            <select className="form-control-smart" value={header.payment_terms} onChange={(e) => setHeader({ ...header, payment_terms: e.target.value })}>
              {PAYMENT_TERMS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="pos-field-label">Payment due date</label>
            <input type="date" className="form-control-smart" value={header.payment_due_date} onChange={(e) => setHeader({ ...header, payment_due_date: e.target.value })} />
          </div>
          <div>
            <label className="pos-field-label">Warehouse / location</label>
            <input className="form-control-smart" value={header.warehouse} onChange={(e) => setHeader({ ...header, warehouse: e.target.value })} />
          </div>
          <div>
            <label className="pos-field-label">Reference no.</label>
            <input className="form-control-smart" value={header.reference_number} onChange={(e) => setHeader({ ...header, reference_number: e.target.value })} />
          </div>
        </div>
        {supplier && (
          <div style={{ marginTop: 12, fontSize: '0.8rem', color: '#475569' }}>
            GSTIN: {supplier.gstin || 'Unregistered'} · {supplier.phone || ''} · {supplier.address || ''}
            <strong style={{ marginLeft: 8, color: interstate ? '#B45309' : '#047857' }}>{interstate ? 'Interstate (IGST)' : 'Same state (CGST+SGST)'}</strong>
          </div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginTop: 12 }}>
          <div>
            <label className="pos-field-label">Transporter</label>
            <input className="form-control-smart" value={header.transporter} onChange={(e) => setHeader({ ...header, transporter: e.target.value })} />
          </div>
          <div>
            <label className="pos-field-label">Vehicle no.</label>
            <input className="form-control-smart" value={header.vehicle_number} onChange={(e) => setHeader({ ...header, vehicle_number: e.target.value })} />
          </div>
          <div>
            <label className="pos-field-label">LR number</label>
            <input className="form-control-smart" value={header.lr_number} onChange={(e) => setHeader({ ...header, lr_number: e.target.value })} />
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <label className="pos-field-label">Notes / delivery instructions</label>
          <textarea className="form-control-smart" rows={2} value={header.notes} onChange={(e) => setHeader({ ...header, notes: e.target.value })} />
        </div>
      </div>

      <div className="smart-card" style={{ padding: 16, marginBottom: 16, overflowX: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <strong>Raw materials</strong>
          <button type="button" className="btn-smart btn-outline-smart" onClick={() => setLines([...lines, emptyLine(defaultGst)])}><Plus size={14} /> Add row</button>
        </div>
        <table className="smart-table">
          <thead>
            <tr>
              <th>#</th><th>Raw material</th><th>HSN</th><th>Qty</th><th>Unit</th><th>Rate</th><th>Disc</th><th>Taxable</th><th>GST%</th><th>Tax</th><th>Total</th><th></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((ln, idx) => {
              const m = preview.rowCalcs[idx] || {};
              return (
                <tr key={idx}>
                  <td>{idx + 1}</td>
                  <td>
                    <select className="form-control-smart" value={ln.raw_material} onChange={(e) => setLine(idx, 'raw_material', e.target.value)}>
                      <option value="">Select...</option>
                      {materials.map((rm) => (
                        <option key={rm.id} value={rm.id}>{rm.name} ({rm.material_code})</option>
                      ))}
                    </select>
                  </td>
                  <td><input className="form-control-smart" value={ln.hsn_code} onChange={(e) => setLine(idx, 'hsn_code', e.target.value)} style={{ width: 80 }} /></td>
                  <td><input type="number" min="0.001" step="any" className="form-control-smart" value={ln.quantity} onChange={(e) => setLine(idx, 'quantity', e.target.value)} style={{ width: 80 }} /></td>
                  <td>{ln.uom}</td>
                  <td><input type="number" min="0" step="0.01" className="form-control-smart" value={ln.unit_cost} onChange={(e) => setLine(idx, 'unit_cost', e.target.value)} style={{ width: 90 }} /></td>
                  <td><input type="number" min="0" step="0.01" className="form-control-smart" value={ln.discount} onChange={(e) => setLine(idx, 'discount', e.target.value)} style={{ width: 80 }} /></td>
                  <td>{money(m.taxable)}</td>
                  <td>
                    <select className="form-control-smart" value={normalizeGstRate(ln.gst_rate, 0)} onChange={(e) => setLine(idx, 'gst_rate', e.target.value)}>
                      {gstOptions.map((g) => <option key={g} value={String(g)}>{g}%</option>)}
                    </select>
                  </td>
                  <td>{money((m.cgst || 0) + (m.sgst || 0) + (m.igst || 0))}</td>
                  <td style={{ fontWeight: 800 }}>{money(m.total)}</td>
                  <td>
                    {lines.length > 1 && (
                      <button type="button" className="btn-smart btn-outline-smart" style={{ color: '#DC2626' }} onClick={() => setLines(lines.filter((_, i) => i !== idx))}><Trash2 size={14} /></button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, alignItems: 'start' }}>
        <div className="smart-card" style={{ padding: 16 }}>
          <strong>Additional charges</strong>
          {charges.map((ch, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr auto auto 32px', gap: 8, marginTop: 8, alignItems: 'end' }}>
              <div>
                <label className="pos-field-label">Charge name</label>
                <input className="form-control-smart" value={ch.name} onChange={(e) => { const n = [...charges]; n[i].name = e.target.value; setCharges(n); }} />
              </div>
              <div>
                <label className="pos-field-label">Amount (₹)</label>
                <input type="number" className="form-control-smart" value={ch.amount} onChange={(e) => { const n = [...charges]; n[i].amount = e.target.value; setCharges(n); }} />
              </div>
              <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 4, paddingBottom: 10 }}>
                <input type="checkbox" checked={ch.gst_applicable} onChange={(e) => { const n = [...charges]; n[i].gst_applicable = e.target.checked; setCharges(n); }} /> GST
              </label>
              <div>
                <label className="pos-field-label">GST %</label>
                <select className="form-control-smart" value={ch.gst_rate} onChange={(e) => { const n = [...charges]; n[i].gst_rate = e.target.value; setCharges(n); }}>
                  {gstOptions.map((g) => <option key={g} value={String(g)}>{g}%</option>)}
                </select>
              </div>
              <button type="button" className="btn-smart btn-outline-smart" onClick={() => setCharges(charges.filter((_, x) => x !== i))}>×</button>
            </div>
          ))}
          <button type="button" className="btn-smart btn-outline-smart" style={{ marginTop: 8 }} onClick={() => setCharges([...charges, { name: '', amount: '', gst_applicable: false, gst_rate: defaultGst }])}>Add charge</button>
        </div>
        <div className="smart-card" style={{ padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>Subtotal</span><strong>{money(preview.subtotal)}</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>Discount</span><strong>{money(preview.discount)}</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>Taxable</span><strong>{money(preview.taxable)}</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>CGST</span><strong>{money(preview.cgst)}</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>SGST</span><strong>{money(preview.sgst)}</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>IGST</span><strong>{money(preview.igst)}</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>Other charges</span><strong>{money(preview.other)}</strong></div>
          <div style={{ marginBottom: 8 }}>
            <label className="pos-field-label">Round off</label>
            <input type="number" step="0.01" className="form-control-smart" value={header.round_off} onChange={(e) => setHeader({ ...header, round_off: e.target.value })} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #E2E8F0', paddingTop: 8, fontSize: '1.1rem' }}>
            <span>Grand total</span><strong style={{ color: '#059669' }}>{money(preview.grand)}</strong>
          </div>
          <p style={{ fontSize: 11, color: '#94A3B8', marginTop: 8 }}>Preview only — saved totals come from the server.</p>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
        <button type="button" className="btn-smart btn-outline-smart" onClick={() => navigate('/purchase-orders')}>Back</button>
        <button type="button" disabled={saving} className="btn-smart btn-outline-smart" onClick={() => save(false)}><Save size={16} /> Save draft</button>
        <button type="button" disabled={saving} className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }} onClick={() => save(true)}><Send size={16} /> Save & place order</button>
      </div>

      {showSupplier && (
        <div className="modal-backdrop" onClick={() => setShowSupplier(false)}>
          <div className="modal-content-smart" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontWeight: 800, marginBottom: 12 }}>Add supplier</h3>
            <form onSubmit={addSupplier}>
              <div className="form-field">
                <label className="form-field-label">Supplier name *</label>
                <input className="form-control-smart" required value={newSup.name} onChange={(e) => setNewSup({ ...newSup, name: e.target.value })} />
              </div>
              <div className="form-field">
                <label className="form-field-label">GSTIN</label>
                <input className="form-control-smart" value={newSup.gstin} onChange={(e) => setNewSup({ ...newSup, gstin: e.target.value })} />
              </div>
              <div className="form-field">
                <label className="form-field-label">Phone</label>
                <input className="form-control-smart" value={newSup.phone} onChange={(e) => setNewSup({ ...newSup, phone: e.target.value })} />
              </div>
              <div className="form-field">
                <label className="form-field-label">State</label>
                <input className="form-control-smart" value={newSup.state} onChange={(e) => setNewSup({ ...newSup, state: e.target.value })} />
              </div>
              <div className="form-field">
                <label className="form-field-label">Address</label>
                <input className="form-control-smart" value={newSup.address} onChange={(e) => setNewSup({ ...newSup, address: e.target.value })} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                <button type="button" className="btn-smart btn-outline-smart" onClick={() => setShowSupplier(false)}>Cancel</button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }}>Save supplier</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
