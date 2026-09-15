import React, { useEffect, useState } from 'react';
import { getBalanceSheet, getCompanySettings } from '../api';
import { Scale, Printer, RefreshCw, TrendingUp, Wallet, Package, Users, Truck } from 'lucide-react';

const money = (n) =>
  `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function BalanceSheet() {
  const [data, setData] = useState(null);
  const [company, setCompany] = useState(null);
  const [asOf, setAsOf] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(true);

  const load = (date = asOf) => {
    setLoading(true);
    Promise.all([
      getBalanceSheet(date),
      getCompanySettings(),
    ])
      .then(([bsRes, csRes]) => {
        setData(bsRes.data);
        const arr = csRes.data.results || csRes.data;
        setCompany(Array.isArray(arr) ? arr[0] : arr);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading && !data) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#64748B' }}>Loading balance sheet…</div>;
  }

  const pl = data?.pl_summary || {};
  const assets = data?.assets?.items || [];
  const liabilities = data?.liabilities?.items || [];
  const equity = data?.equity?.items || [];
  const companyName = data?.company_name || company?.company_name || 'Your Business';
  const gstin = company?.gstin || '';

  return (
    <div className="balance-sheet-page">
      {/* ─── Screen-only controls ─── */}
      <div className="no-print" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#0F172A', display: 'flex', alignItems: 'center', gap: 10 }}>
            <Scale size={26} color="#059669" /> Balance Sheet
          </h1>
          <p style={{ fontSize: '0.85rem', color: '#64748B', marginTop: 4 }}>
            {companyName} · As on {data?.as_of}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input type="date" className="form-control-smart" value={asOf} onChange={(e) => setAsOf(e.target.value)} style={{ width: 160 }} />
          <button type="button" className="btn-smart btn-outline-smart" onClick={() => load(asOf)}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button type="button" className="btn-smart btn-outline-smart" onClick={() => window.print()}>
            <Printer size={16} /> Print
          </button>
        </div>
      </div>

      {/* ─── P&L Summary cards (screen only) ─── */}
      <div className="stats-grid no-print" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total Sales', value: pl.total_sales, color: '#059669', Icon: TrendingUp, cls: 'icon-green' },
          { label: 'Purchases (Received)', value: pl.total_purchases_received, color: '#DC2626', Icon: Truck, cls: 'icon-blue' },
          { label: 'Gross Profit', value: pl.gross_profit, color: Number(pl.gross_profit) >= 0 ? '#059669' : '#DC2626', Icon: Wallet, cls: 'icon-green' },
          { label: 'Customer Dues (A/R)', value: pl.total_outstanding, color: '#EA580C', Icon: Users, cls: 'icon-blue' },
        ].map((c) => (
          <div key={c.label} className="stat-card">
            <div><div className="stat-label">{c.label}</div><div className="stat-value" style={{ color: c.color }}>{money(c.value)}</div></div>
            <div className={`stat-icon ${c.cls}`}><c.Icon size={22} /></div>
          </div>
        ))}
      </div>

      {/* ─── PRINT HEADER (only visible when printing) ─── */}
      <div className="print-only bs-print-header">
        <div style={{ textAlign: 'center', marginBottom: 8 }}>
          <div style={{ fontSize: 18, fontWeight: 800, textTransform: 'uppercase' }}>{companyName}</div>
          {company?.address_line1 && <div style={{ fontSize: 11 }}>{company.address_line1}{company.address_line2 ? `, ${company.address_line2}` : ''}</div>}
          {(company?.city || company?.state) && <div style={{ fontSize: 11 }}>{[company.city, company.state, company.postal_code].filter(Boolean).join(', ')}</div>}
          {gstin && <div style={{ fontSize: 11 }}><strong>GSTIN:</strong> {gstin}</div>}
          {company?.phone && <div style={{ fontSize: 11 }}>Phone: {company.phone}</div>}
        </div>
        <div style={{ textAlign: 'center', borderTop: '2px solid #000', borderBottom: '2px solid #000', padding: '6px 0', marginBottom: 10 }}>
          <strong style={{ fontSize: 16, letterSpacing: 1 }}>BALANCE SHEET</strong>
          <div style={{ fontSize: 11 }}>As on {data?.as_of}</div>
        </div>
      </div>

      {/* ─── Logo watermark (print only) ─── */}
      <img src="/logo.png" className="print-only bs-watermark" alt="" />

      {/* ─── Main balance sheet table ─── */}
      <div className="smart-card bs-main-card" style={{ marginBottom: 24 }}>
        <div className="card-header-smart no-print" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontWeight: 800, fontSize: '1.05rem' }}>Statement of Financial Position</div>
          <div style={{ fontSize: '0.8rem', color: '#64748B' }}>As on {data?.as_of}</div>
        </div>

        <table className="bs-table">
          <thead>
            <tr>
              <th colSpan={2} style={{ background: '#ECFDF5', color: '#047857' }}>ASSETS</th>
              <th colSpan={2} style={{ background: '#FEF2F2', color: '#B91C1C' }}>LIABILITIES &amp; EQUITY</th>
            </tr>
          </thead>
          <tbody>
            {(() => {
              const rightRows = [...liabilities.map((r) => ({ ...r, section: 'liability' })), ...equity.map((r) => ({ ...r, section: 'equity' }))];
              const maxLen = Math.max(assets.length, rightRows.length);
              const rows = [];
              for (let i = 0; i < maxLen; i++) {
                const a = assets[i];
                const r = rightRows[i];
                rows.push(
                  <tr key={i}>
                    <td>{a?.label || ''}</td>
                    <td className="bs-amt">{a ? money(a.amount) : ''}</td>
                    <td style={r?.section === 'equity' && i === rightRows.findIndex((x) => x.section === 'equity') ? { borderTop: '2px solid #1D4ED8', fontWeight: 700, color: '#1D4ED8' } : {}}>
                      {r?.section === 'equity' && i === rightRows.findIndex((x) => x.section === 'equity')
                        ? <strong>EQUITY</strong> : ''}
                      {r?.section === 'equity' && i === rightRows.findIndex((x) => x.section === 'equity') ? <br /> : null}
                      {r?.label || ''}
                    </td>
                    <td className="bs-amt" style={r?.section === 'equity' ? { color: '#1D4ED8' } : {}}>
                      {r ? money(r.amount) : ''}
                    </td>
                  </tr>
                );
              }
              return rows;
            })()}
          </tbody>
          <tfoot>
            <tr className="bs-total-row">
              <td><strong>Total Assets</strong></td>
              <td className="bs-amt"><strong>{money(data?.totals?.total_assets)}</strong></td>
              <td><strong>Total Liabilities + Equity</strong></td>
              <td className="bs-amt"><strong>{money(data?.totals?.liabilities_plus_equity)}</strong></td>
            </tr>
          </tfoot>
        </table>

        {data?.totals?.is_balanced && (
          <div style={{ padding: '8px 20px', background: '#ECFDF5', color: '#047857', fontSize: '0.85rem', fontWeight: 600, textAlign: 'center' }}>
            ✓ Balance sheet is balanced — Assets ({money(data?.totals?.total_assets)}) = Liabilities + Equity ({money(data?.totals?.liabilities_plus_equity)})
          </div>
        )}
      </div>

      {/* ─── P&L print section (print only) ─── */}
      <div className="print-only bs-pl-print" style={{ marginBottom: 12 }}>
        <table className="bs-table" style={{ fontSize: 11 }}>
          <thead>
            <tr><th colSpan={2} style={{ background: '#F8FAFC', color: '#0F172A' }}>PROFIT &amp; LOSS SUMMARY</th></tr>
          </thead>
          <tbody>
            <tr><td>Total Sales</td><td className="bs-amt">{money(pl.total_sales)}</td></tr>
            <tr><td>Total Purchases (Received POs)</td><td className="bs-amt">{money(pl.total_purchases_received)}</td></tr>
            <tr style={{ fontWeight: 800 }}><td>Gross Profit</td><td className="bs-amt">{money(pl.gross_profit)}</td></tr>
            <tr><td>Total Cash / Bank Collections</td><td className="bs-amt">{money(pl.total_collections)}</td></tr>
            <tr><td>Total Outstanding (A/R)</td><td className="bs-amt">{money(pl.total_outstanding)}</td></tr>
            <tr><td>Output GST (Sales)</td><td className="bs-amt">{money(pl.sales_gst)}</td></tr>
            <tr><td>Input GST (Purchases)</td><td className="bs-amt">{money(pl.purchase_gst)}</td></tr>
          </tbody>
        </table>
      </div>

      {/* ─── Print footer ─── */}
      <div className="print-only" style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#475569' }}>
        <div>
          <div>Notes:</div>
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            {(data?.notes || []).slice(0, 3).map((n) => <li key={n}>{n}</li>)}
          </ul>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ marginTop: 40, borderTop: '1px solid #000', paddingTop: 4, width: 140, marginLeft: 'auto' }}>Authorised Signatory</div>
          <div style={{ marginTop: 4, fontSize: 9 }}>Computer Generated Statement</div>
        </div>
      </div>

      {/* ─── GST & notes (screen only) ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }} className="no-print">
        <div className="smart-card" style={{ padding: 20 }}>
          <div style={{ fontWeight: 800, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Package size={18} color="#059669" /> GST Summary
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.9rem' }}>
            <span>Output GST (on Sales)</span><strong>{money(pl.sales_gst)}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.9rem' }}>
            <span>Input GST (on Purchases)</span><strong>{money(pl.purchase_gst)}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.9rem' }}>
            <span>Net GST Payable</span>
            <strong style={{ color: '#DC2626' }}>{money(liabilities.find((l) => l.key === 'gst_payable')?.amount)}</strong>
          </div>
          {Number(pl.gst_input_credit) > 0 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
              <span>GST Input Credit</span><strong style={{ color: '#059669' }}>{money(pl.gst_input_credit)}</strong>
            </div>
          )}
        </div>
        <div className="smart-card" style={{ padding: 20 }}>
          <div style={{ fontWeight: 800, marginBottom: 12 }}>How this is calculated</div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: '0.85rem', color: '#64748B', lineHeight: 1.7 }}>
            {(data?.notes || []).map((note) => <li key={note}>{note}</li>)}
          </ul>
        </div>
      </div>

      <style>{`
        .print-only { display: none; }
        .bs-table { width: 100%; border-collapse: collapse; }
        .bs-table th, .bs-table td { border: 1px solid #E2E8F0; padding: 8px 14px; font-size: 0.9rem; text-align: left; }
        .bs-table th { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; }
        .bs-amt { text-align: right; font-family: monospace; font-weight: 600; white-space: nowrap; }
        .bs-total-row { background: #0F172A; color: #fff; }
        .bs-total-row td { border-color: #0F172A; padding: 10px 14px; font-size: 0.95rem; }
        .bs-watermark {
          position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
          width: 300px; opacity: 0.06; pointer-events: none; z-index: 0;
        }
        @media print {
          .no-print { display: none !important; }
          .print-only { display: block !important; }
          .balance-sheet-page { padding: 0; }
          .smart-card, .bs-main-card { box-shadow: none !important; border: 1px solid #000 !important; border-radius: 0 !important; }
          .bs-table th, .bs-table td { border-color: #000; }
          .bs-total-row { background: #000 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .bs-total-row td { border-color: #000; color: #fff; }
          .card-header-smart { display: none !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          @page { margin: 10mm; }
        }
      `}</style>
    </div>
  );
}
