import React, { useEffect, useState } from 'react';
import { getStock } from '../api';
import { Boxes, AlertTriangle, CheckCircle2, Search } from 'lucide-react';

export default function Stock() {
  const [stockList, setStockList] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all'); // 'all', 'low', 'healthy'
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStock()
      .then((res) => {
        setStockList(res.data.results || res.data);
        setLoading(false);
      })
      .catch(console.error);
  }, []);

  const filteredStock = stockList.filter((st) => {
    const isLow = st.quantity <= st.low_stock_threshold;
    const matchesSearch = st.product_name.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (!matchesSearch) return false;
    if (filterType === 'low') return isLow;
    if (filterType === 'healthy') return !isLow;
    return true;
  });

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Stock Inventory Monitor...</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Real-time Stock Monitor</h1>
        <p style={{ fontSize: '0.85rem', color: '#64748B' }}>Live product inventory quantities and low-stock reorder thresholds.</p>
      </div>

      <div className="smart-card">
        {/* Search & Filter Bar */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #E2E8F0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: '380px' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Search stock product name..."
              className="form-control-smart"
              style={{ paddingLeft: '38px', height: '38px', backgroundColor: '#F8FAFC' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setFilterType('all')}
              className={`btn-smart ${filterType === 'all' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
              style={{ padding: '6px 14px', fontSize: '0.8rem' }}
            >
              All Items ({stockList.length})
            </button>
            <button
              onClick={() => setFilterType('low')}
              className={`btn-smart ${filterType === 'low' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
              style={{ padding: '6px 14px', fontSize: '0.8rem', backgroundColor: filterType === 'low' ? '#DC2626' : undefined }}
            >
              Low Stock ({stockList.filter(s => s.quantity <= s.low_stock_threshold).length})
            </button>
            <button
              onClick={() => setFilterType('healthy')}
              className={`btn-smart ${filterType === 'healthy' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
              style={{ padding: '6px 14px', fontSize: '0.8rem', backgroundColor: filterType === 'healthy' ? '#166534' : undefined }}
            >
              Healthy Stock
            </button>
          </div>
        </div>

        <table className="smart-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Current Quantity</th>
              <th>Batches remaining</th>
              <th>Reorder Threshold</th>
              <th>Stock Status</th>
              <th>Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {filteredStock.map((st) => {
              const isLow = st.quantity <= st.low_stock_threshold;
              return (
                <tr key={st.id}>
                  <td style={{ fontWeight: '700', color: '#0F172A' }}>{st.product_name}</td>
                  <td style={{ fontWeight: '800', fontSize: '1rem', color: isLow ? '#DC2626' : '#15803D' }}>{st.quantity}</td>
                  <td>
                    {(st.batches || []).length === 0 ? (
                      <span style={{ color: '#94A3B8' }}>—</span>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {st.batches.map((b) => (
                          <span
                            key={b.id}
                            className="badge-smart"
                            style={{
                              backgroundColor: Number(b.remaining_quantity) > 0 ? '#ECFDF5' : '#F1F5F9',
                              color: Number(b.remaining_quantity) > 0 ? '#047857' : '#94A3B8',
                              width: 'fit-content',
                            }}
                          >
                            {b.batch_number}: {Number(b.remaining_quantity).toFixed(2)} left
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td>{st.low_stock_threshold}</td>
                  <td>
                    {isLow ? (
                      <span className="badge-smart badge-overdue" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <AlertTriangle size={12} /> Low Stock Alert
                      </span>
                    ) : (
                      <span className="badge-smart badge-paid" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle2 size={12} /> Healthy Stock
                      </span>
                    )}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: '#64748B' }}>{st.updated_at ? new Date(st.updated_at).toLocaleString() : '-'}</td>
                </tr>
              );
            })}
            {filteredStock.length === 0 && (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '32px', color: '#94A3B8' }}>
                  {searchTerm ? `No stock records match "${searchTerm}"` : 'No stock records available.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
