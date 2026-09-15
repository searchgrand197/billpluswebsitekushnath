import React, { useEffect, useState } from 'react';
import { getDashboardData } from '../api';
import { IndianRupee, FileText, Package, AlertTriangle, TrendingUp, PlusCircle, Leaf, Factory, Boxes, CheckCircle2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getDashboardData()
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching dashboard metrics:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Ayurvedic ERP Dashboard...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Ayurvedic ERP Executive Dashboard</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748B' }}>Real-time sales, raw material inventory, manufacturing batches, and ledger overview.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <Link to="/manufacturing" className="btn-smart btn-outline-smart" style={{ textDecoration: 'none' }}>
            <Factory size={16} /> New Batch
          </Link>
          <Link to="/pos" className="btn-smart btn-primary-smart" style={{ textDecoration: 'none', backgroundColor: '#059669' }}>
            <PlusCircle size={18} /> New Bill
          </Link>
        </div>
      </div>

      {/* Top Stat Cards Grid */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        {/* Today's Sales */}
        <div className="stat-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/invoices')}>
          <div>
            <div className="stat-label">Today's Sales</div>
            <div className="stat-value" style={{ color: '#059669' }}>
              ₹{Number(data?.today_sales || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <small style={{ fontSize: '0.75rem', color: '#64748B', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
              <TrendingUp size={14} color="#059669" /> {data?.today_bills || 0} Bills Issued Today
            </small>
          </div>
          <div className="stat-icon icon-green">
            <IndianRupee size={24} />
          </div>
        </div>

        {/* Low Stock Raw Materials */}
        <div
          className="stat-card"
          style={{ cursor: 'pointer', borderColor: data?.low_stock_raw_materials > 0 ? '#FCA5A5' : undefined }}
          onClick={() => navigate('/raw-materials')}
        >
          <div>
            <div className="stat-label">Low Stock Raw Materials</div>
            <div className="stat-value" style={{ color: data?.low_stock_raw_materials > 0 ? '#DC2626' : '#059669' }}>
              {data?.low_stock_raw_materials || 0} Ingredients
            </div>
            <small style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '4px', display: 'block' }}>Requires Reordering</small>
          </div>
          <div className="stat-icon icon-orange">
            <Leaf size={24} />
          </div>
        </div>

        {/* Low Stock Finished Products */}
        <div
          className="stat-card"
          style={{ cursor: 'pointer', borderColor: data?.low_stock_finished_products > 0 ? '#FCA5A5' : undefined }}
          onClick={() => navigate('/stock')}
        >
          <div>
            <div className="stat-label">Low Stock Finished Goods</div>
            <div className="stat-value" style={{ color: data?.low_stock_finished_products > 0 ? '#DC2626' : '#059669' }}>
              {data?.low_stock_finished_products || 0} Products
            </div>
            <small style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '4px', display: 'block' }}>Low Stock Alert</small>
          </div>
          <div className="stat-icon icon-purple">
            <AlertTriangle size={24} />
          </div>
        </div>

        {/* Today's Manufacturing */}
        <div className="stat-card" style={{ cursor: 'pointer' }} onClick={() => navigate('/manufacturing')}>
          <div>
            <div className="stat-label">Today's Manufacturing</div>
            <div className="stat-value" style={{ color: '#0284C7' }}>
              {data?.today_mfg_count || 0} Batches
            </div>
            <small style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '4px', display: 'block' }}>Production Log</small>
          </div>
          <div className="stat-icon icon-blue">
            <Factory size={24} />
          </div>
        </div>
      </div>

      {/* Secondary Valuation Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="stat-card">
          <div>
            <div className="stat-label">Raw Material Valuation</div>
            <div className="stat-value" style={{ color: '#047857', fontSize: '1.25rem' }}>
              ₹{Number(data?.total_raw_material_stock_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <small style={{ fontSize: '0.75rem', color: '#64748B' }}>Herb & Ingredient Assets</small>
          </div>
          <div className="stat-icon icon-green"><Leaf size={20} /></div>
        </div>

        <div className="stat-card">
          <div>
            <div className="stat-label">Finished Stock Valuation</div>
            <div className="stat-value" style={{ color: '#0F172A', fontSize: '1.25rem' }}>
              ₹{Number(data?.total_finished_stock_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <small style={{ fontSize: '0.75rem', color: '#64748B' }}>{data?.total_products || 0} Catalog Items</small>
          </div>
          <div className="stat-icon icon-purple"><Boxes size={20} /></div>
        </div>
      </div>

      {/* Two Column Section */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Recent Bills */}
        <div className="smart-card">
          <div className="card-header-smart">
            <div style={{ fontWeight: '700', color: '#0F172A' }}>Recent Sales Invoices</div>
            <Link to="/invoices" style={{ fontSize: '0.8rem', color: '#059669', fontWeight: '600', textDecoration: 'none' }}>
              View Sales History →
            </Link>
          </div>
          <table className="smart-table">
            <thead>
              <tr>
                <th>Invoice #</th>
                <th>Customer</th>
                <th>Amount</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data?.recent_invoices?.map((inv) => (
                <tr key={inv.id}>
                  <td style={{ fontWeight: '700', color: '#059669' }}>{inv.invoice_number}</td>
                  <td>{inv.customer_name || 'Walk-in Customer'}</td>
                  <td style={{ fontWeight: '700' }}>₹{Number(inv.total_amount).toFixed(2)}</td>
                  <td>
                    <span className={`badge-smart badge-${inv.status === 'paid' ? 'paid' : inv.status === 'credit' ? 'credit' : 'pending'}`}>
                      {inv.status?.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
              {(!data?.recent_invoices || data.recent_invoices.length === 0) && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', color: '#94A3B8', padding: '24px' }}>No invoices logged yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Recent Manufacturing Logs */}
        <div className="smart-card">
          <div className="card-header-smart">
            <div style={{ fontWeight: '700', color: '#0F172A', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Factory size={18} color="#059669" />
              Recent Production Batches
            </div>
            <Link to="/manufacturing" style={{ fontSize: '0.8rem', color: '#059669', fontWeight: '600', textDecoration: 'none' }}>
              Manufacturing Log →
            </Link>
          </div>
          <table className="smart-table">
            <thead>
              <tr>
                <th>Mfg ID</th>
                <th>Product</th>
                <th>Batch #</th>
                <th>Qty</th>
              </tr>
            </thead>
            <tbody>
              {data?.recent_mfg?.map((mfg) => (
                <tr key={mfg.id}>
                  <td style={{ fontWeight: '700', color: '#059669' }}>{mfg.manufacturing_id}</td>
                  <td style={{ fontWeight: '600' }}>{mfg.product_name}</td>
                  <td><span className="badge-smart" style={{ backgroundColor: '#ECFDF5', color: '#047857' }}>{mfg.batch_number}</span></td>
                  <td style={{ fontWeight: '700' }}>{Number(mfg.production_quantity).toFixed(2)}</td>
                </tr>
              ))}
              {(!data?.recent_mfg || data.recent_mfg.length === 0) && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', color: '#94A3B8', padding: '24px' }}>No manufacturing batches completed yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
