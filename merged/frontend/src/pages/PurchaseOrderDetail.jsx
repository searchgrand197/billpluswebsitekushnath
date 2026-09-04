import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { getPurchaseOrder, getCompanySettings, placePurchaseOrder, receivePurchaseOrder, duplicatePurchaseOrder } from '../api';
import { Printer, PackageCheck, Copy, Send } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import { money, STATUS_STYLE, statusLabel } from './poUtils';

export default function PurchaseOrderDetail() {
  const { id } = useParams();
  const [po, setPo] = useState(null);
  const [settings, setSettings] = useState(null);
  const [receiveMode, setReceiveMode] = useState(false);
  const [recv, setRecv] = useState({});
  const [saving, setSaving] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const load = () => {
    getPurchaseOrder(id).then((r) => {
      setPo(r.data);
      const init = {};
      (r.data.items || []).forEach((it) => {
        init[it.id] = { quantity: '', batch_number: '', mfg_date: '', expiry_date: '', location: '', supplier_batch_number: '' };
      });
      setRecv(init);
    });
  };

  useEffect(() => {
    load();
    getCompanySettings().then((r) => setSettings((r.data.results || r.data)[0] || null));
  }, [id]);

  useEffect(() => {
    if (params.get('print') && po) {
      setTimeout(() => window.print(), 400);
    }
    if (params.get('receive') && po && ['ordered', 'partially_received'].includes(po.status)) {
      setReceiveMode(true);
    }
  }, [params, po]);

  if (!po) return <div style={{ padding: 40, color: '#64748B' }}>Loading purchase order...</div>;
  const st = STATUS_STYLE[po.status] || STATUS_STYLE.draft;

  const submitReceive = () => {
    const items = Object.entries(recv)
      .map(([po_item, v]) => ({ po_item: Number(po_item), ...v, quantity: Number(v.quantity) || 0 }))
      .filter((x) => x.quantity > 0);
    if (!items.length) {
      toast.showError('Enter received quantity for at least one line.');
      return;
    }
    setSaving(true);
    receivePurchaseOrder(id, { items, received_by: 'Store' })
      .then((res) => {
        toast.showSuccess(res.data.status === 'received' ? 'Purchase Order fully received. Stock updated.' : 'Purchase Order partially received. Stock updated.');
        setReceiveMode(false);
        setPo(res.data);
      })
      .catch((e) => toast.showError(e.response?.data?.error || 'Receive failed.'))
      .finally(() => setSaving(false));
  };

  return (
    <div className="po-print-root">
      <div className="no-print" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, gap: 8, flexWrap: 'wrap' }}>
        <div>
          <Link to="/purchase-orders" style={{ fontSize: 13, color: '#059669' }}>← Purchase orders</Link>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800 }}>{po.order_number}</h1>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {po.status === 'draft' && (
            <button className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }} onClick={() => placePurchaseOrder(id).then((r) => { setPo(r.data); toast.showSuccess('Purchase Order approved / ordered.'); })}>
              <Send size={14} /> Place order
            </button>
          )}
          {['ordered', 'partially_received'].includes(po.status) && (
            <button className="btn-smart btn-outline-smart" onClick={() => setReceiveMode(true)}><PackageCheck size={14} /> Receive</button>
          )}
          {['draft', 'ordered'].includes(po.status) && (
            <Link to={`/purchase-orders/${id}/edit`} className="btn-smart btn-outline-smart" style={{ textDecoration: 'none' }}>Edit</Link>
          )}
          <button className="btn-smart btn-outline-smart" onClick={() => duplicatePurchaseOrder(id).then((r) => navigate(`/purchase-orders/${r.data.id}/edit`))}><Copy size={14} /> Duplicate</button>
          <button className="btn-smart btn-outline-smart" onClick={() => window.print()}><Printer size={14} /> Print / PDF</button>
        </div>
      </div>

      <div className="smart-card" style={{ padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #E2E8F0', paddingBottom: 12, marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 900, fontSize: '1.2rem', color: '#059669' }}>{settings?.company_name || 'BILLVICE'}</div>
            <div style={{ fontSize: 13, color: '#64748B' }}>{settings?.address_line1} {settings?.city} {settings?.state}</div>
            <div style={{ fontSize: 13 }}>GSTIN: {settings?.gstin || '—'}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontWeight: 800 }}>PURCHASE ORDER</div>
            <span className="badge-smart" style={{ backgroundColor: st.bg, color: st.color }}>{statusLabel(po.status)}</span>
            <div style={{ marginTop: 6 }}>Date: {po.order_date}</div>
            {po.expected_delivery_date && <div>Expected: {po.expected_delivery_date}</div>}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, color: '#64748B' }}>SUPPLIER</div>
            <div style={{ fontWeight: 700 }}>{po.supplier_name}</div>
            <div style={{ fontSize: 13 }}>{po.supplier_address}</div>
            <div style={{ fontSize: 13 }}>GSTIN: {po.supplier_gstin || 'Unregistered'} · {po.supplier_phone}</div>
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, color: '#64748B' }}>DELIVERY</div>
            <div style={{ fontSize: 13 }}>{po.warehouse || po.delivery_address || '—'}</div>
            <div style={{ fontSize: 13 }}>{po.transporter} {po.vehicle_number} {po.lr_number}</div>
            <div style={{ fontSize: 13 }}>Payment: {po.payment_terms} {po.payment_due_date ? `· Due ${po.payment_due_date}` : ''}</div>
          </div>
        </div>

        <table className="smart-table">
          <thead>
            <tr>
              <th>#</th><th>Item</th><th>HSN</th><th>Qty</th><th>Received</th><th>Unit</th><th>Rate</th><th>Disc</th><th>Taxable</th><th>GST</th><th>Total</th>
            </tr>
          </thead>
          <tbody>
            {(po.items || []).map((it, i) => (
              <tr key={it.id}>
                <td>{i + 1}</td>
                <td style={{ fontWeight: 700 }}>{it.raw_material_name || it.product_name}</td>
                <td>{it.hsn_code || '—'}</td>
                <td>{Number(it.quantity).toFixed(3)}</td>
                <td>{Number(it.received_quantity || 0).toFixed(3)}</td>
                <td>{it.uom}</td>
                <td>{money(it.unit_cost)}</td>
                <td>{money(it.discount)}</td>
                <td>{money(it.taxable_amount)}</td>
                <td>{money(Number(it.cgst) + Number(it.sgst) + Number(it.igst))}</td>
                <td style={{ fontWeight: 800 }}>{money(it.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={{ maxWidth: 320, marginLeft: 'auto', marginTop: 16, fontSize: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Taxable</span><span>{money(po.taxable_amount)}</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>CGST</span><span>{money(po.cgst_amount)}</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>SGST</span><span>{money(po.sgst_amount)}</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>IGST</span><span>{money(po.igst_amount)}</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Other charges</span><span>{money(po.other_charges)}</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Round off</span><span>{money(po.round_off)}</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 800, fontSize: 18, marginTop: 8 }}><span>Grand total</span><span>{money(po.total_amount)}</span></div>
          <div style={{ marginTop: 8, fontSize: 12, color: '#475569' }}>{po.amount_in_words}</div>
        </div>

        {po.notes && <p style={{ marginTop: 16, fontSize: 13 }}><strong>Notes:</strong> {po.notes}</p>}
        {(po.terms || settings?.invoice_footer_text) && (
          <div style={{ marginTop: 16, fontSize: 12, color: '#475569' }}>
            <strong>Terms & conditions</strong>
            <p>{po.terms || settings?.invoice_footer_text}</p>
          </div>
        )}
        {po.cancelled_reason && <p style={{ marginTop: 8, color: '#B91C1C' }}><strong>Cancelled:</strong> {po.cancelled_reason}</p>}

        {(po.receipts || []).length > 0 && (
          <div className="no-print" style={{ marginTop: 20 }}>
            <h3 style={{ fontSize: '1rem' }}>Receipt history</h3>
            {(po.receipts || []).map((grn) => (
              <div key={grn.id} style={{ fontSize: 13, padding: '8px 0', borderBottom: '1px solid #F1F5F9' }}>
                <strong>{grn.receipt_number}</strong> · {grn.receipt_date}
                {(grn.items || []).map((ri) => (
                  <div key={ri.id}>+{Number(ri.quantity).toFixed(3)} {ri.raw_material_name} {ri.batch_number ? `· Batch ${ri.batch_number}` : ''}</div>
                ))}
              </div>
            ))}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 24, marginTop: 40, fontSize: 12, color: '#64748B' }}>
          <div>Prepared by<br /><br />________________</div>
          <div>Authorized by<br /><br />________________</div>
          <div>Supplier acceptance<br /><br />________________</div>
        </div>
      </div>

      {receiveMode && (
        <div className="modal-backdrop no-print" onClick={() => setReceiveMode(false)}>
          <div className="modal-content-smart" style={{ maxWidth: 720, maxHeight: '90vh', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontWeight: 800, marginBottom: 8 }}>Purchase inward / receive</h3>
            <p style={{ fontSize: 13, color: '#64748B', marginBottom: 12 }}>Stock increases only for quantities entered below.</p>
            {(po.items || []).map((it) => (
              <div key={it.id} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 12, marginBottom: 10 }}>
                <div style={{ fontWeight: 700 }}>{it.raw_material_name}</div>
                <div style={{ fontSize: 12, color: '#64748B' }}>
                  Ordered {Number(it.quantity).toFixed(3)} · Received {Number(it.received_quantity || 0).toFixed(3)} · Remaining {Number(it.remaining_quantity).toFixed(3)} {it.uom}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 8 }}>
                  <input type="number" className="form-control-smart" placeholder="This receipt qty" value={recv[it.id]?.quantity || ''} onChange={(e) => setRecv({ ...recv, [it.id]: { ...recv[it.id], quantity: e.target.value } })} />
                  <input className="form-control-smart" placeholder="Batch no." value={recv[it.id]?.batch_number || ''} onChange={(e) => setRecv({ ...recv, [it.id]: { ...recv[it.id], batch_number: e.target.value } })} />
                  <input className="form-control-smart" placeholder="Location" value={recv[it.id]?.location || ''} onChange={(e) => setRecv({ ...recv, [it.id]: { ...recv[it.id], location: e.target.value } })} />
                  <input type="date" className="form-control-smart" value={recv[it.id]?.mfg_date || ''} onChange={(e) => setRecv({ ...recv, [it.id]: { ...recv[it.id], mfg_date: e.target.value } })} />
                  <input type="date" className="form-control-smart" value={recv[it.id]?.expiry_date || ''} onChange={(e) => setRecv({ ...recv, [it.id]: { ...recv[it.id], expiry_date: e.target.value } })} />
                  <input className="form-control-smart" placeholder="Supplier batch" value={recv[it.id]?.supplier_batch_number || ''} onChange={(e) => setRecv({ ...recv, [it.id]: { ...recv[it.id], supplier_batch_number: e.target.value } })} />
                </div>
              </div>
            ))}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="btn-smart btn-outline-smart" onClick={() => setReceiveMode(false)}>Back</button>
              <button disabled={saving} className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }} onClick={submitReceive}>Save inward & update stock</button>
            </div>
          </div>
        </div>
      )}

      <style>{`@media print { .no-print, .sidebar, .navbar, .app-container > aside { display:none !important; } .main-content { margin:0 !important; } }`}</style>
    </div>
  );
}
