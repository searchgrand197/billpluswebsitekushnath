import React, { useEffect, useState } from 'react';
import { getProducts, getCategories, createProduct, updateProduct, updateProductStock, deleteProduct, getCompanySettings } from '../api';
import { Plus, Search, Trash2, Pencil } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import ConfirmationModal from '../components/ConfirmationModal';
import PricingGstCard from '../components/PricingGstCard';
import { money, normalizeGstRate, beforeFromInclusive, sellingGstMath } from './poUtils';
import { PRODUCT_UOM_OPTIONS } from '../unitUtils';

export default function Products() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const toast = useToast();

  const [showAddModal, setShowAddModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState('');
  const [sku, setSku] = useState('');
  const [hsn, setHsn] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [uom, setUom] = useState('unit');
  const [priceMode, setPriceMode] = useState('before');
  const [costPrice, setCostPrice] = useState('');
  const [sellingBefore, setSellingBefore] = useState('');
  const [sellingAfter, setSellingAfter] = useState('');
  const [gstRate, setGstRate] = useState('5');
  const [stockQty, setStockQty] = useState('');
  const [stockMin, setStockMin] = useState('');
  const [detail, setDetail] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchData();
    getCompanySettings().then((r) => {
      const list = r.data.results || r.data;
      const s = list[0] || null;
      setSettings(s);
      if (s?.gst_percentage != null) setGstRate(normalizeGstRate(s.gst_percentage, 5));
    });
  }, []);

  const fetchData = () => {
    getProducts().then((res) => {
      setProducts(res.data.results || res.data);
      setLoading(false);
    });
    getCategories().then((res) => setCategories(res.data.results || res.data));
  };

  const resetForm = (product = null) => {
    if (product) {
      setEditing(product);
      setName(product.name);
      setSku(product.sku || '');
      setHsn(product.hsn_code || '');
      setCategoryId(product.category ? String(product.category) : '');
      setUom(product.uom || 'unit');
      setPriceMode('before');
      setCostPrice(String(product.cost_price ?? ''));
      setSellingBefore(String(product.price ?? ''));
      setSellingAfter(String(product.selling_price_after_gst ?? ''));
      setGstRate(normalizeGstRate(product.gst_rate, settings?.gst_percentage ?? 5));
      setStockQty(String(product.stock?.quantity ?? '0'));
      setStockMin(String(product.stock?.low_stock_threshold ?? '5'));
    } else {
      setEditing(null);
      setName('');
      setSku('');
      setHsn('');
      setCategoryId('');
      setUom('unit');
      setPriceMode('before');
      setCostPrice('');
      setSellingBefore('');
      setSellingAfter('');
      setGstRate(normalizeGstRate(settings?.gst_percentage, 5));
      setStockQty('0');
      setStockMin('5');
    }
  };

  const openEdit = (product, e) => {
    e?.stopPropagation?.();
    resetForm(product);
    setDetail(null);
    setShowAddModal(true);
  };

  const handleSaveProduct = (e) => {
    e.preventDefault();
    const gst = Number(gstRate);
    const math = priceMode === 'after'
      ? beforeFromInclusive(sellingAfter, gst)
      : sellingGstMath(sellingBefore, gst);
    if (!name.trim() || math.before < 0) {
      toast.showWarning('Product name and selling price are required.');
      return;
    }
    const generatedSku = sku.trim() || `SKU-${Math.floor(1000 + Math.random() * 9000)}`;
    const payload = {
      name: name.trim(),
      sku: generatedSku,
      hsn_code: hsn,
      uom,
      category: categoryId || null,
      cost_price: Number(costPrice || 0),
      price: math.before,
      gst_rate: gst,
      price_mode: 'before',
    };
    setSaving(true);
    const req = editing ? updateProduct(editing.id, payload) : createProduct(payload);
    req
      .then(async (res) => {
        const saved = res.data;
        const productId = editing?.id || saved?.id;
        if (productId && (stockQty !== '' || stockMin !== '')) {
          try {
            await updateProductStock(productId, {
              quantity: Number(stockQty || 0),
              low_stock_threshold: Number(stockMin || 0),
            });
          } catch (stockErr) {
            toast.showWarning('Product saved, but stock update failed.');
          }
        }
        toast.showSuccess(editing ? `Product '${name}' updated.` : `Product '${name}' created.`);
        setShowAddModal(false);
        resetForm();
        fetchData();
      })
      .catch((err) => {
        const errMsg =
          err.response?.data?.sku?.[0] ||
          err.response?.data?.price?.[0] ||
          err.response?.data?.gst_rate?.[0] ||
          err.response?.data?.detail ||
          'Failed to save product.';
        toast.showError(errMsg);
      })
      .finally(() => setSaving(false));
  };

  const filteredProducts = products.filter((p) => {
    const term = searchTerm.toLowerCase();
    const catName = categories.find((c) => c.id === p.category)?.name || '';
    return (
      p.name.toLowerCase().includes(term) ||
      (p.sku && p.sku.toLowerCase().includes(term)) ||
      (p.hsn_code && p.hsn_code.toLowerCase().includes(term)) ||
      catName.toLowerCase().includes(term) ||
      String(p.price).includes(term)
    );
  });

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Products Catalog...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Items Catalog & Prices</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748B' }}>Purchase price, selling price before GST, and selling price after GST are kept separate.</p>
        </div>
        <button onClick={() => { resetForm(); setShowAddModal(true); }} className="btn-smart btn-primary-smart">
          <Plus size={18} /> Add New Item
        </button>
      </div>

      <div className="smart-card">
        <div className="card-header-smart" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ position: 'relative', width: '320px' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Search product name, SKU, HSN, or category..."
              className="form-control-smart"
              style={{ paddingLeft: '38px', height: '38px', backgroundColor: '#F8FAFC' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <span style={{ fontSize: '0.85rem', color: '#64748B', fontWeight: '600' }}>
            Showing {filteredProducts.length} of {products.length} products
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="smart-table">
            <thead>
              <tr>
                <th>Item / SKU</th>
                <th>Category</th>
                <th>HSN</th>
                <th>Purchase</th>
                <th>Sell (before GST)</th>
                <th>GST %</th>
                <th>Sell (after GST)</th>
                <th>Stock</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProducts.map((p) => (
                <tr key={p.id} style={{ cursor: 'pointer' }} onClick={() => setDetail(p)}>
                  <td>
                    <div style={{ fontWeight: 700 }}>{p.name}</div>
                    <div style={{ fontSize: 12, color: '#64748B' }}>{p.sku || '—'}</div>
                  </td>
                  <td>
                    <span className="badge-smart" style={{ backgroundColor: '#F1F5F9', color: '#475569' }}>
                      {p.category_name || 'General'}
                    </span>
                  </td>
                  <td>{p.hsn_code || '—'}</td>
                  <td>{money(p.cost_price)}</td>
                  <td>{money(p.price)}</td>
                  <td>{Number(p.gst_rate || 0)}%</td>
                  <td style={{ fontWeight: 800, color: '#15803D' }}>{money(p.selling_price_after_gst)}</td>
                  <td style={{ fontWeight: 700, color: (p.stock?.quantity || 0) <= (p.stock?.low_stock_threshold || 5) ? '#DC2626' : '#0F172A' }}>
                    {p.stock?.quantity || 0} {p.uom}
                  </td>
                  <td style={{ textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="btn-smart btn-outline-smart"
                      style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      onClick={(e) => openEdit(p, e)}
                      title="Edit product"
                    >
                      <Pencil size={14} /> Edit
                    </button>
                  </td>
                </tr>
              ))}
              {filteredProducts.length === 0 && (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '32px', color: '#94A3B8' }}>
                    No items found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showAddModal && (
        <div className="modal-backdrop" onClick={() => !saving && setShowAddModal(false)}>
          <div className="modal-content-smart" style={{ maxWidth: 560, maxHeight: '90vh', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontWeight: '700', marginBottom: '16px' }}>{editing ? 'Edit Product' : 'Add Product Item'}</h3>
            <form onSubmit={handleSaveProduct}>
              <div style={{ marginBottom: '12px' }}>
                <label className="pos-field-label">Item Name *</label>
                <input type="text" className="form-control-smart" required placeholder="e.g. Ashwagandha Churna 100g" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div>
                  <label className="pos-field-label">Category</label>
                  <select className="form-control-smart" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                    <option value="">Select Category...</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>{cat.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="pos-field-label">Unit</label>
                  <select className="form-control-smart" value={uom} onChange={(e) => setUom(e.target.value)}>
                    {PRODUCT_UOM_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="pos-field-label">SKU</label>
                  <input type="text" className="form-control-smart" placeholder="Auto if empty" value={sku} onChange={(e) => setSku(e.target.value)} />
                </div>
                <div>
                  <label className="pos-field-label">HSN / SAC</label>
                  <input type="text" className="form-control-smart" value={hsn} onChange={(e) => setHsn(e.target.value)} />
                </div>
                <div>
                  <label className="pos-field-label">Stock Qty</label>
                  <input type="number" step="0.001" min="0" className="form-control-smart" value={stockQty} onChange={(e) => setStockQty(e.target.value)} />
                </div>
                <div>
                  <label className="pos-field-label">Low Stock Alert At</label>
                  <input type="number" step="0.001" min="0" className="form-control-smart" value={stockMin} onChange={(e) => setStockMin(e.target.value)} />
                </div>
              </div>
              <PricingGstCard
                settings={settings}
                costPrice={costPrice}
                sellingBefore={sellingBefore}
                sellingAfter={sellingAfter}
                gstRate={gstRate}
                priceMode={priceMode}
                onChange={(next) => {
                  setCostPrice(next.costPrice);
                  setSellingBefore(next.sellingBefore);
                  setSellingAfter(next.sellingAfter);
                  setGstRate(next.gstRate);
                  setPriceMode(next.priceMode);
                }}
              />
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: 16 }}>
                <button type="button" className="btn-smart btn-secondary-smart" disabled={saving} onClick={() => setShowAddModal(false)}>Cancel</button>
                <button type="submit" className="btn-smart btn-primary-smart" disabled={saving}>
                  {saving ? 'Saving…' : editing ? 'Update Product' : 'Save Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {detail && (
        <div className="modal-backdrop" onClick={() => setDetail(null)}>
          <div className="modal-content-smart" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontWeight: 800, marginBottom: 8 }}>{detail.name}</h3>
            <p style={{ fontSize: 13, color: '#64748B', marginBottom: 12 }}>{detail.sku} · {detail.category_name || 'General'} · HSN {detail.hsn_code || '—'}</p>
            <div style={{ border: '1px solid #E2E8F0', borderRadius: 12, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>Purchase price before GST</span><strong>{money(detail.cost_price)}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>Selling price before GST</span><strong>{money(detail.price)}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>GST rate</span><strong>{Number(detail.gst_rate || 0)}%</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span>GST amount</span><strong>{money(detail.gst_amount)}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, paddingTop: 8, borderTop: '1px solid #E2E8F0' }}>
                <span>Selling price after GST</span><strong style={{ color: '#059669', fontSize: '1.15rem' }}>{money(detail.selling_price_after_gst)}</strong>
              </div>
            </div>
            <p style={{ fontSize: 13, color: '#64748B', marginTop: 12 }}>Stock: {detail.stock?.quantity || 0} {detail.uom} · Min {detail.stock?.low_stock_threshold || 0}</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <button type="button" className="btn-smart btn-outline-smart" onClick={() => setDetail(null)}>Close</button>
              <button type="button" className="btn-smart btn-outline-smart" style={{ color: '#DC2626' }} onClick={() => { setDeleteTarget(detail); }}>
                <Trash2 size={14} /> Delete
              </button>
              <button type="button" className="btn-smart btn-primary-smart" onClick={() => openEdit(detail)}>
                <Pencil size={14} /> Edit
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmationModal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete product"
        message={`Delete “${deleteTarget?.name || ''}”? This cannot be undone if the item is unused.`}
        confirmText="Delete"
        isDanger
        loading={deleting}
        onConfirm={() => {
          setDeleting(true);
          deleteProduct(deleteTarget.id)
            .then(() => {
              toast.showSuccess('Product deleted.');
              setDeleteTarget(null);
              setDetail(null);
              fetchData();
            })
            .catch((err) => toast.showError(err.response?.data?.error || 'Could not delete product.'))
            .finally(() => setDeleting(false));
        }}
      />
    </div>
  );
}
