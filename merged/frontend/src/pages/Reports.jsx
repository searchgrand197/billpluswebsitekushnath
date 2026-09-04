import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getReportsSummary, getRawMaterials, getManufacturingLogs, getStockMovements, getCustomers, getPurchaseGstReport } from '../api';
import { BarChart3, TrendingUp, IndianRupee, ShoppingBag, Users, FileText, Printer, Leaf, Factory, Boxes, Download, Truck, Scale } from 'lucide-react';

export default function Reports() {
  const [reportTab, setReportTab] = useState('sales'); // 'sales', 'inventory', 'manufacturing', 'customers'
  const [reports, setReports] = useState(null);
  const [rawMaterials, setRawMaterials] = useState([]);
  const [mfgLogs, setMfgLogs] = useState([]);
  const [movements, setMovements] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [gstReport, setGstReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getReportsSummary(),
      getRawMaterials(),
      getManufacturingLogs(),
      getStockMovements(),
      getCustomers(),
      getPurchaseGstReport(),
    ])
      .then(([repRes, rmRes, mfgRes, movRes, custRes, gstRes]) => {
        setReports(repRes.data);
        setRawMaterials(rmRes.data.results || rmRes.data);
        setMfgLogs(mfgRes.data.results || mfgRes.data);
        setMovements(movRes.data.results || movRes.data);
        setCustomers(custRes.data.results || custRes.data);
        setGstReport(gstRes.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handlePrintReport = () => {
    window.print();
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Ayurvedic ERP Reports...</div>;
  }

  const rawMaterialValuation = rawMaterials.reduce((acc, m) => acc + Number(m.current_stock) * Number(m.purchase_price), 0);
  const totalCustomerDues = customers.reduce((acc, c) => acc + Number(c.outstanding_balance || 0), 0);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Ayurvedic ERP Reports & Analytics</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748B' }}>Comprehensive sales, raw material, manufacturing, and customer debt reports.</p>
        </div>
        <button onClick={handlePrintReport} className="btn-smart btn-outline-smart">
          <Printer size={16} /> Print Report Statement
        </button>
      </div>

      {/* Report Categories Navigation */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #E2E8F0', marginBottom: '24px' }}>
        <button
          onClick={() => setReportTab('sales')}
          className={`btn-smart ${reportTab === 'sales' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
          style={{ backgroundColor: reportTab === 'sales' ? '#059669' : undefined, borderRadius: '8px 8px 0 0' }}
        >
          <FileText size={16} /> Sales & Revenue Reports
        </button>
        <button
          onClick={() => setReportTab('inventory')}
          className={`btn-smart ${reportTab === 'inventory' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
          style={{ backgroundColor: reportTab === 'inventory' ? '#059669' : undefined, borderRadius: '8px 8px 0 0' }}
        >
          <Leaf size={16} /> Inventory & Raw Material Valuation
        </button>
        <button
          onClick={() => setReportTab('manufacturing')}
          className={`btn-smart ${reportTab === 'manufacturing' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
          style={{ backgroundColor: reportTab === 'manufacturing' ? '#059669' : undefined, borderRadius: '8px 8px 0 0' }}
        >
          <Factory size={16} /> Manufacturing & Consumption
        </button>
        <button
          onClick={() => setReportTab('customers')}
          className={`btn-smart ${reportTab === 'customers' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
          style={{ backgroundColor: reportTab === 'customers' ? '#059669' : undefined, borderRadius: '8px 8px 0 0' }}
        >
          <Users size={16} /> Customer Debtors (A/R)
        </button>
        <button
          onClick={() => setReportTab('purchase-gst')}
          className={`btn-smart ${reportTab === 'purchase-gst' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
          style={{ backgroundColor: reportTab === 'purchase-gst' ? '#059669' : undefined, borderRadius: '8px 8px 0 0' }}
        >
          <Truck size={16} /> Purchase GST
        </button>
        <Link to="/balance-sheet" className="btn-smart btn-outline-smart" style={{ borderRadius: '8px 8px 0 0', textDecoration: 'none', marginLeft: 'auto' }}>
          <Scale size={16} /> Balance Sheet →
        </Link>
      </div>

      {/* Report 1: Sales */}
      {reportTab === 'sales' && (
        <div>
          <div className="stats-grid" style={{ marginBottom: '24px' }}>
            <div className="stat-card">
              <div>
                <div className="stat-label">Gross Revenue</div>
                <div className="stat-value" style={{ color: '#059669' }}>
                  ₹{Number(reports?.total_sales || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <small style={{ fontSize: '0.75rem', color: '#64748B' }}>Total Completed Sales</small>
              </div>
              <div className="stat-icon icon-green"><IndianRupee size={24} /></div>
            </div>

            <div className="stat-card">
              <div>
                <div className="stat-label">Total Bills Issued</div>
                <div className="stat-value">{reports?.total_orders || 0}</div>
                <small style={{ fontSize: '0.75rem', color: '#64748B' }}>Invoice Volume</small>
              </div>
              <div className="stat-icon icon-blue"><FileText size={24} /></div>
            </div>
          </div>

          <div className="smart-card">
            <div className="card-header-smart"><div style={{ fontWeight: '700' }}>Sales Breakdown Audit</div></div>
            <table className="smart-table">
              <thead>
                <tr>
                  <th>Bill #</th>
                  <th>Customer</th>
                  <th>Bill Date</th>
                  <th>Subtotal</th>
                  <th>Tax Amount</th>
                  <th>Grand Total</th>
                </tr>
              </thead>
              <tbody>
                {reports?.recent_invoices?.map((inv) => (
                  <tr key={inv.id}>
                    <td style={{ fontWeight: '700', color: '#059669' }}>{inv.invoice_number}</td>
                    <td style={{ fontWeight: '600' }}>{inv.customer_name || 'Walk-in Customer'}</td>
                    <td>{inv.invoice_date}</td>
                    <td>₹{Number(inv.subtotal).toFixed(2)}</td>
                    <td>₹{(Number(inv.cgst_amount || 0) + Number(inv.sgst_amount || 0)).toFixed(2)}</td>
                    <td style={{ fontWeight: '800', color: '#0F172A' }}>₹{Number(inv.total_amount).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Report 2: Inventory */}
      {reportTab === 'inventory' && (
        <div>
          <div className="stats-grid" style={{ marginBottom: '24px' }}>
            <div className="stat-card">
              <div>
                <div className="stat-label">Raw Material Stock Valuation</div>
                <div className="stat-value" style={{ color: '#059669' }}>
                  ₹{rawMaterialValuation.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <small style={{ fontSize: '0.75rem', color: '#64748B' }}>{rawMaterials.length} Active Ingredients</small>
              </div>
              <div className="stat-icon icon-green"><Leaf size={24} /></div>
            </div>
          </div>

          <div className="smart-card">
            <div className="card-header-smart"><div style={{ fontWeight: '700' }}>Raw Material Stock Valuation Statement</div></div>
            <table className="smart-table">
              <thead>
                <tr>
                  <th>Material Code</th>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Current Stock</th>
                  <th>Cost / Unit</th>
                  <th>Total Valuation</th>
                </tr>
              </thead>
              <tbody>
                {rawMaterials.map((m) => (
                  <tr key={m.id}>
                    <td style={{ fontWeight: '700', color: '#059669' }}>{m.material_code}</td>
                    <td style={{ fontWeight: '700' }}>{m.name}</td>
                    <td>{m.category}</td>
                    <td>{Number(m.current_stock).toFixed(2)} {m.unit}</td>
                    <td>₹{Number(m.purchase_price).toFixed(2)}</td>
                    <td style={{ fontWeight: '800' }}>₹{(Number(m.current_stock) * Number(m.purchase_price)).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Report 3: Manufacturing */}
      {reportTab === 'manufacturing' && (
        <div className="smart-card">
          <div className="card-header-smart"><div style={{ fontWeight: '700' }}>Manufacturing Production & Cost Report</div></div>
          <table className="smart-table">
            <thead>
              <tr>
                <th>Mfg ID</th>
                <th>Finished Product</th>
                <th>Batch Number</th>
                <th>Quantity Produced</th>
                <th>Batch Cost</th>
                <th>Date</th>
                <th>Operator</th>
              </tr>
            </thead>
            <tbody>
              {mfgLogs.map((log) => (
                <tr key={log.id}>
                  <td style={{ fontWeight: '700', color: '#059669' }}>{log.manufacturing_id}</td>
                  <td style={{ fontWeight: '700' }}>{log.product_name}</td>
                  <td><span className="badge-smart" style={{ backgroundColor: '#ECFDF5', color: '#047857' }}>{log.batch_number}</span></td>
                  <td style={{ fontWeight: '800' }}>{Number(log.production_quantity).toFixed(2)} units</td>
                  <td style={{ fontWeight: '700' }}>₹{Number(log.total_cost).toFixed(2)}</td>
                  <td>{log.mfg_date}</td>
                  <td>{log.operator || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Report 4: Customers */}
      {reportTab === 'customers' && (
        <div>
          <div className="stats-grid" style={{ marginBottom: '24px' }}>
            <div className="stat-card">
              <div>
                <div className="stat-label">Total Outstanding Debt (A/R)</div>
                <div className="stat-value" style={{ color: '#DC2626' }}>
                  ₹{totalCustomerDues.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <small style={{ fontSize: '0.75rem', color: '#DC2626' }}>Total Outstanding Balance</small>
              </div>
              <div className="stat-icon icon-orange"><Users size={24} /></div>
            </div>
          </div>

          <div className="smart-card">
            <div className="card-header-smart"><div style={{ fontWeight: '700' }}>Customer Debtors & Outstanding Balance Report</div></div>
            <table className="smart-table">
              <thead>
                <tr>
                  <th>Customer Name</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th>Outstanding Balance</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: '700', color: '#0F172A' }}>{c.name}</td>
                    <td>{c.phone || '-'}</td>
                    <td>{c.email || '-'}</td>
                    <td style={{ fontWeight: '800', color: Number(c.outstanding_balance) > 0 ? '#DC2626' : '#047857' }}>
                      ₹{Number(c.outstanding_balance || 0).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {reportTab === 'purchase-gst' && (
        <div>
          <div className="stats-grid" style={{ marginBottom: '24px' }}>
            <div className="stat-card">
              <div>
                <div className="stat-label">Taxable Purchases</div>
                <div className="stat-value">₹{Number(gstReport?.taxable || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
              </div>
            </div>
            <div className="stat-card">
              <div>
                <div className="stat-label">CGST</div>
                <div className="stat-value">₹{Number(gstReport?.cgst || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
              </div>
            </div>
            <div className="stat-card">
              <div>
                <div className="stat-label">SGST</div>
                <div className="stat-value">₹{Number(gstReport?.sgst || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
              </div>
            </div>
            <div className="stat-card">
              <div>
                <div className="stat-label">IGST</div>
                <div className="stat-value">₹{Number(gstReport?.igst || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
              </div>
            </div>
            <div className="stat-card">
              <div>
                <div className="stat-label">Purchase Total</div>
                <div className="stat-value" style={{ color: '#059669' }}>₹{Number(gstReport?.total || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
              </div>
            </div>
          </div>
          <div className="smart-card">
            <div className="card-header-smart"><div style={{ fontWeight: 700 }}>Purchase orders (GST)</div></div>
            <table className="smart-table">
              <thead>
                <tr>
                  <th>PO</th><th>Date</th><th>Supplier</th><th>Taxable</th><th>CGST</th><th>SGST</th><th>IGST</th><th>Total</th>
                </tr>
              </thead>
              <tbody>
                {(gstReport?.orders || []).map((po) => (
                  <tr key={po.id}>
                    <td style={{ fontWeight: 700 }}>{po.order_number}</td>
                    <td>{po.order_date}</td>
                    <td>{po.supplier_name}</td>
                    <td>₹{Number(po.taxable_amount || 0).toFixed(2)}</td>
                    <td>₹{Number(po.cgst_amount || 0).toFixed(2)}</td>
                    <td>₹{Number(po.sgst_amount || 0).toFixed(2)}</td>
                    <td>₹{Number(po.igst_amount || 0).toFixed(2)}</td>
                    <td>₹{Number(po.total_amount || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
