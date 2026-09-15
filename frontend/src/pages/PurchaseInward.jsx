import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getPendingReceipts } from '../api';
import { money, STATUS_STYLE, statusLabel } from './poUtils';

export default function PurchaseInward() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    getPendingReceipts().then((r) => setRows(r.data.results || r.data));
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Purchase inward / pending receipts</h1>
      <p style={{ color: '#64748B', fontSize: '0.85rem', marginBottom: 16 }}>Only these ordered POs can increase raw-material stock when you receive goods.</p>
      <div className="smart-card">
        <table className="smart-table">
          <thead>
            <tr><th>PO</th><th>Supplier</th><th>Date</th><th>Status</th><th>Pending value</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((po) => {
              const st = STATUS_STYLE[po.status] || STATUS_STYLE.ordered;
              return (
                <tr key={po.id}>
                  <td style={{ fontWeight: 800, color: '#059669' }}>{po.order_number}</td>
                  <td>{po.supplier_name}</td>
                  <td>{po.order_date}</td>
                  <td><span className="badge-smart" style={{ backgroundColor: st.bg, color: st.color }}>{statusLabel(po.status)}</span></td>
                  <td>{money(po.pending_amount)}</td>
                  <td><Link to={`/purchase-orders/${po.id}?receive=1`} className="btn-smart btn-outline-smart" style={{ textDecoration: 'none' }}>Receive</Link></td>
                </tr>
              );
            })}
            {rows.length === 0 && <tr><td colSpan="6" style={{ textAlign: 'center', padding: 28, color: '#94A3B8' }}>Nothing pending receipt.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
