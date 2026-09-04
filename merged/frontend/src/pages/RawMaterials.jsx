import React, { useEffect, useState } from 'react';
import { getRawMaterials, createRawMaterial, updateRawMaterial, adjustRawMaterialStock, getRawMaterialHistory, getCompanySettings } from '../api';
import { Leaf, Plus, Search, AlertTriangle, CheckCircle2, Edit3, ArrowUpRight, ArrowDownRight, History, X } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import { allowedGstRates, normalizeGstRate } from './poUtils';
import { RAW_MATERIAL_UNIT_OPTIONS, formatQtyDisplay } from '../unitUtils';

export default function RawMaterials() {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all'); // 'all', 'low'

  const [showAddModal, setShowAddModal] = useState(false);
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyData, setHistoryData] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Add/Edit Form State
  const [materialCode, setMaterialCode] = useState('');
  const [name, setName] = useState('');
  const [category, setCategory] = useState('Herbs');
  const [unit, setUnit] = useState('g');
  const [currentStock, setCurrentStock] = useState('0');
  const [minimumStock, setMinimumStock] = useState('5');
  const [purchasePrice, setPurchasePrice] = useState('0');
  const [supplier, setSupplier] = useState('');
  const [batchNumber, setBatchNumber] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [location, setLocation] = useState('');
  const [notes, setNotes] = useState('');
  const [hsnCode, setHsnCode] = useState('');
  const [gstRate, setGstRate] = useState('5');
  const [settings, setSettings] = useState(null);

  // Stock Adjust State
  const [adjustChange, setAdjustChange] = useState('');
  const [adjustReason, setAdjustReason] = useState('Stock Purchase / Entry');

  const toast = useToast();

  useEffect(() => {
    fetchMaterials();
    getCompanySettings().then((r) => {
      const s = (r.data.results || r.data)[0] || null;
      setSettings(s);
      if (s?.gst_percentage != null) setGstRate(normalizeGstRate(s.gst_percentage, 5));
    });
  }, []);

  const fetchMaterials = () => {
    getRawMaterials()
      .then((res) => {
        setMaterials(res.data.results || res.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  };

  const handleOpenAddModal = (mat = null) => {
    if (mat) {
      setSelectedMaterial(mat);
      setMaterialCode(mat.material_code);
      setName(mat.name);
      setCategory(mat.category);
      setUnit(mat.unit);
      setCurrentStock(String(mat.current_stock));
      setMinimumStock(String(mat.minimum_stock));
      setPurchasePrice(String(mat.purchase_price));
      setSupplier(mat.supplier || '');
      setBatchNumber(mat.batch_number || '');
      setExpiryDate(mat.expiry_date || '');
      setLocation(mat.location || '');
      setNotes(mat.notes || '');
      setHsnCode(mat.hsn_code || '');
      setGstRate(normalizeGstRate(mat.gst_rate, settings?.gst_percentage ?? 5));
    } else {
      setSelectedMaterial(null);
      setMaterialCode(`RM-${Math.floor(1000 + Math.random() * 9000)}`);
      setName('');
      setCategory('Herbs');
      setUnit('kg');
      setCurrentStock('0');
      setMinimumStock('5');
      setPurchasePrice('0');
      setSupplier('');
      setBatchNumber('');
      setExpiryDate('');
      setLocation('');
      setNotes('');
      setHsnCode('');
      setGstRate(normalizeGstRate(settings?.gst_percentage, 5));
    }
    setShowAddModal(true);
  };

  const handleSaveMaterial = (e) => {
    e.preventDefault();
    if (!name || !materialCode) {
      toast.showError('Material Name and Code are required.');
      return;
    }

    const payload = {
      material_code: materialCode,
      name,
      category,
      unit,
      current_stock: Number(currentStock) || 0,
      minimum_stock: Number(minimumStock) || 0,
      purchase_price: Number(purchasePrice) || 0,
      supplier,
      batch_number: batchNumber,
      expiry_date: expiryDate || null,
      location,
      notes,
      hsn_code: hsnCode,
      gst_rate: Number(gstRate) || 0,
    };

    if (selectedMaterial) {
      updateRawMaterial(selectedMaterial.id, payload)
        .then(() => {
          toast.showSuccess(`Raw Material '${name}' updated successfully.`);
          setShowAddModal(false);
          fetchMaterials();
        })
        .catch((err) => {
          toast.showError(err.response?.data?.detail || 'Failed to update raw material.');
        });
    } else {
      createRawMaterial(payload)
        .then(() => {
          toast.showSuccess(`Raw Material '${name}' created successfully.`);
          setShowAddModal(false);
          fetchMaterials();
        })
        .catch((err) => {
          toast.showError(err.response?.data?.material_code?.[0] || 'Failed to create raw material.');
        });
    }
  };

  const loadHistory = (materialId) => {
    setHistoryLoading(true);
    getRawMaterialHistory(materialId)
      .then((res) => {
        setHistoryData(res.data);
        setHistoryLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setHistoryLoading(false);
        toast.showError('Failed to load stock history.');
      });
  };

  const handleOpenHistory = (mat) => {
    setSelectedMaterial(mat);
    setShowHistoryModal(true);
    setHistoryData(null);
    loadHistory(mat.id);
  };

  const formatStockQty = (qty, unit) => formatQtyDisplay(qty, unit);

  const movementLabel = (type) => {
    const map = {
      opening_stock: 'Opening stock',
      purchase: 'Purchase / stock in',
      manufacturing_consumption: 'Consumed into finished product',
      manufacturing_output: 'Manufacturing output',
      sale: 'Sale',
      sale_cancellation: 'Sale cancelled',
      adjustment: 'Manual adjustment',
      return: 'Return',
    };
    return map[type] || type;
  };

  const handleAdjustStockSubmit = (e) => {
    e.preventDefault();
    if (!selectedMaterial || !adjustChange) return;

    adjustRawMaterialStock(selectedMaterial.id, {
      quantity_change: Number(adjustChange),
      reason: adjustReason,
    })
      .then(() => {
        toast.showSuccess(`Stock adjusted for '${selectedMaterial.name}'.`);
        setShowAdjustModal(false);
        setAdjustChange('');
        fetchMaterials();
        if (showHistoryModal && selectedMaterial) {
          loadHistory(selectedMaterial.id);
        }
      })
      .catch((err) => {
        toast.showError(err.response?.data?.error || 'Stock adjustment failed.');
      });
  };

  const filteredMaterials = materials.filter((m) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      m.name.toLowerCase().includes(term) ||
      m.material_code.toLowerCase().includes(term) ||
      m.category.toLowerCase().includes(term);
    const isLow = Number(m.current_stock) <= Number(m.minimum_stock);

    if (!matchesSearch) return false;
    if (filterType === 'low') return isLow;
    return true;
  });

  const totalStockValue = materials.reduce((acc, m) => acc + Number(m.current_stock) * Number(m.purchase_price), 0);
  const lowStockCount = materials.filter((m) => Number(m.current_stock) <= Number(m.minimum_stock)).length;

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Raw Materials Master...</div>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Raw Material Inventory</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748B' }}>
            Manage herbs, powders, extracts, oils, and ingredient stock for Ayurvedic production.
          </p>
        </div>
        <button onClick={() => handleOpenAddModal(null)} className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }}>
          <Plus size={18} /> Add Raw Material
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="stat-card">
          <div>
            <div className="stat-label">Total Raw Materials</div>
            <div className="stat-value">{materials.length}</div>
            <small style={{ fontSize: '0.75rem', color: '#64748B' }}>Active Ingredients</small>
          </div>
          <div className="stat-icon icon-green"><Leaf size={24} /></div>
        </div>

        <div className="stat-card">
          <div>
            <div className="stat-label">Total Material Stock Value</div>
            <div className="stat-value" style={{ color: '#059669' }}>₹{totalStockValue.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
            <small style={{ fontSize: '0.75rem', color: '#64748B' }}>Valuation at Cost</small>
          </div>
          <div className="stat-icon icon-blue"><CheckCircle2 size={24} /></div>
        </div>

        <div className="stat-card" style={{ borderColor: lowStockCount > 0 ? '#FCA5A5' : undefined }}>
          <div>
            <div className="stat-label">Low Stock Ingredients</div>
            <div className="stat-value" style={{ color: lowStockCount > 0 ? '#DC2626' : '#166534' }}>{lowStockCount}</div>
            <small style={{ fontSize: '0.75rem', color: '#64748B' }}>Requires Reorder</small>
          </div>
          <div className="stat-icon icon-orange"><AlertTriangle size={24} /></div>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="smart-card">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #E2E8F0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: '380px' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
            <input
              type="text"
              placeholder="Search by code, herb name, category..."
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
              style={{ padding: '6px 14px', fontSize: '0.8rem', backgroundColor: filterType === 'all' ? '#059669' : undefined }}
            >
              All Items ({materials.length})
            </button>
            <button
              onClick={() => setFilterType('low')}
              className={`btn-smart ${filterType === 'low' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
              style={{ padding: '6px 14px', fontSize: '0.8rem', backgroundColor: filterType === 'low' ? '#DC2626' : undefined }}
            >
              Low Stock Alerts ({lowStockCount})
            </button>
          </div>
        </div>

        <table className="smart-table">
          <thead>
            <tr>
              <th>Material Code</th>
              <th>Material / Herb Name</th>
              <th>Category</th>
              <th>Current Stock</th>
              <th>Min Threshold</th>
              <th>Cost Price / Unit</th>
              <th>GST %</th>
              <th>HSN</th>
              <th>Supplier</th>
              <th>Status</th>
              <th style={{ textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredMaterials.map((m) => {
              const isLow = Number(m.current_stock) <= Number(m.minimum_stock);
              return (
                <tr key={m.id}>
                  <td style={{ fontWeight: '700', color: '#059669' }}>{m.material_code}</td>
                  <td style={{ fontWeight: '700', color: '#0F172A' }}>{m.name}</td>
                  <td><span className="badge-smart" style={{ backgroundColor: '#ECFDF5', color: '#047857' }}>{m.category}</span></td>
                  <td style={{ fontWeight: '800', fontSize: '1rem', color: isLow ? '#DC2626' : '#047857' }}>
                    {formatStockQty(m.current_stock, m.unit)}
                  </td>
                  <td style={{ color: '#64748B' }}>{formatStockQty(m.minimum_stock, m.unit)}</td>
                  <td style={{ fontWeight: '700' }}>₹{Number(m.purchase_price).toFixed(2)}</td>
                  <td>{Number(m.gst_rate || 0)}%</td>
                  <td>{m.hsn_code || '—'}</td>
                  <td style={{ color: '#64748B' }}>{m.supplier || '-'}</td>
                  <td>
                    {isLow ? (
                      <span className="badge-smart badge-overdue" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <AlertTriangle size={12} /> Low Stock
                      </span>
                    ) : (
                      <span className="badge-smart badge-paid" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle2 size={12} /> Available
                      </span>
                    )}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '6px' }}>
                      <button
                        onClick={() => handleOpenHistory(m)}
                        className="btn-smart btn-outline-smart"
                        style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        title="Stock History"
                      >
                        <History size={14} /> History
                      </button>
                      <button
                        onClick={() => {
                          setSelectedMaterial(m);
                          setAdjustChange('');
                          setShowAdjustModal(true);
                        }}
                        className="btn-smart btn-outline-smart"
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                        title="Adjust Stock"
                      >
                        Adjust Stock
                      </button>
                      <button
                        onClick={() => handleOpenAddModal(m)}
                        className="btn-smart btn-outline-smart"
                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                        title="Edit Material"
                      >
                        <Edit3 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {filteredMaterials.length === 0 && (
              <tr>
                <td colSpan="11" style={{ textAlign: 'center', padding: '32px', color: '#94A3B8' }}>
                  {searchTerm ? `No raw materials found matching "${searchTerm}"` : 'No raw materials added yet.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Add / Edit Material Modal */}
      {showAddModal && (
        <div className="modal-backdrop" onClick={() => setShowAddModal(false)}>
          <div className="modal-content-smart" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '640px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '800', marginBottom: '16px', color: '#0F172A' }}>
              {selectedMaterial ? 'Edit Raw Material' : 'Add New Raw Material'}
            </h2>
            <form onSubmit={handleSaveMaterial}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    MATERIAL CODE *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. RM-5085"
                    className="form-control-smart"
                    value={materialCode}
                    onChange={(e) => setMaterialCode(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    HERB / INGREDIENT NAME *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Sesame Oil, Ashwagandha, Honey"
                    className="form-control-smart"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    CATEGORY *
                  </label>
                  <select className="form-control-smart" value={category} onChange={(e) => setCategory(e.target.value)}>
                    <option value="Herbs">Herbs</option>
                    <option value="Powders">Powders</option>
                    <option value="Oils">Oils & Liquids</option>
                    <option value="Extracts">Extracts</option>
                    <option value="Packaging">Packaging Material</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    UNIT OF MEASURE (UOM) *
                  </label>
                  <select className="form-control-smart" value={unit} onChange={(e) => setUnit(e.target.value)}>
                    {RAW_MATERIAL_UNIT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>For medicine ingredients use mg or g. Stock is stored in this unit.</div>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    PURCHASE PRICE BEFORE GST / UNIT (₹)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="e.g. 250.00"
                    className="form-control-smart"
                    value={purchasePrice}
                    onChange={(e) => setPurchasePrice(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    GST RATE (%)
                  </label>
                  <select className="form-control-smart" value={normalizeGstRate(gstRate, settings?.gst_percentage ?? 5)} onChange={(e) => setGstRate(e.target.value)}>
                    {allowedGstRates(settings).map((g) => (
                      <option key={g} value={String(g)}>{g}%</option>
                    ))}
                  </select>
                  <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>Default from Settings GST. Used when adding this material to a Purchase Order.</div>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    HSN / SAC
                  </label>
                  <input
                    type="text"
                    className="form-control-smart"
                    value={hsnCode}
                    onChange={(e) => setHsnCode(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    INITIAL / CURRENT STOCK QTY
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    min="0"
                    placeholder="e.g. 10.00"
                    className="form-control-smart"
                    value={currentStock}
                    onChange={(e) => setCurrentStock(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    MINIMUM STOCK ALERT LEVEL
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    min="0"
                    placeholder="e.g. 5.00"
                    className="form-control-smart"
                    value={minimumStock}
                    onChange={(e) => setMinimumStock(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    SUPPLIER / VENDOR NAME
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Herbal Traders Co."
                    className="form-control-smart"
                    value={supplier}
                    onChange={(e) => setSupplier(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '800', color: '#334155', marginBottom: '6px', letterSpacing: '0.04em' }}>
                    STORAGE LOCATION / RACK
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Shelf A-3"
                    className="form-control-smart"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
                <button type="button" onClick={() => setShowAddModal(false)} className="btn-smart btn-outline-smart">
                  Cancel
                </button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }}>
                  {selectedMaterial ? 'Save Changes' : 'Create Raw Material'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Adjust Stock Modal */}
      {showAdjustModal && selectedMaterial && (
        <div className="modal-backdrop" onClick={() => setShowAdjustModal(false)}>
          <div className="modal-content-smart" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '440px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '800', marginBottom: '8px', color: '#0F172A' }}>
              Adjust Stock: {selectedMaterial.name}
            </h2>
            <p style={{ fontSize: '0.85rem', color: '#64748B', marginBottom: '16px' }}>
              Current stock balance: <strong>{Number(selectedMaterial.current_stock).toFixed(2)} {selectedMaterial.unit}</strong>
            </p>
            <form onSubmit={handleAdjustStockSubmit}>
              <div style={{ marginBottom: '12px' }}>
                <label className="pos-field-label">QUANTITY CHANGE (+ FOR ADD, - FOR REDUCE) *</label>
                <input
                  type="number"
                  step="0.001"
                  required
                  placeholder="e.g. +10 or -2.5"
                  className="form-control-smart"
                  value={adjustChange}
                  onChange={(e) => setAdjustChange(e.target.value)}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label className="pos-field-label">REASON FOR ADJUSTMENT</label>
                <input
                  type="text"
                  className="form-control-smart"
                  value={adjustReason}
                  onChange={(e) => setAdjustReason(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button type="button" onClick={() => setShowAdjustModal(false)} className="btn-smart btn-outline-smart">
                  Cancel
                </button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }}>
                  Update Stock
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showHistoryModal && selectedMaterial && (
        <div className="modal-backdrop" onClick={() => setShowHistoryModal(false)}>
          <div className="modal-content-smart" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '720px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#0F172A', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <History size={20} color="#059669" /> Stock History
                </h2>
                <p style={{ fontSize: '0.85rem', color: '#64748B', marginTop: '4px' }}>
                  {selectedMaterial.material_code} · {selectedMaterial.name} · Current: {formatStockQty(selectedMaterial.current_stock, selectedMaterial.unit)}
                </p>
              </div>
              <button type="button" onClick={() => setShowHistoryModal(false)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#64748B' }}>
                <X size={20} />
              </button>
            </div>

            {historyLoading && (
              <div style={{ padding: '24px', textAlign: 'center', color: '#64748B' }}>Loading audit timeline...</div>
            )}

            {!historyLoading && historyData && (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '20px' }}>
                  <div style={{ padding: '12px', backgroundColor: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#64748B', textTransform: 'uppercase' }}>Stock in</div>
                    <div style={{ fontWeight: '800', color: '#0F172A' }}>{formatStockQty(historyData.qty_in, historyData.unit)}</div>
                  </div>
                  <div style={{ padding: '12px', backgroundColor: '#FEF2F2', borderRadius: '8px', border: '1px solid #FECACA' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#991B1B', textTransform: 'uppercase' }}>Consumed into finished goods</div>
                    <div style={{ fontWeight: '800', color: '#B91C1C' }}>{formatStockQty(historyData.qty_consumed, historyData.unit)}</div>
                  </div>
                  <div style={{ padding: '12px', backgroundColor: '#ECFDF5', borderRadius: '8px', border: '1px solid #A7F3D0' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: '700', color: '#047857', textTransform: 'uppercase' }}>₹ spent into finished products</div>
                    <div style={{ fontWeight: '800', color: '#065F46' }}>₹{Number(historyData.spent_into_finished_products || 0).toFixed(2)}</div>
                  </div>
                </div>

                {(!historyData.movements || historyData.movements.length === 0) && (
                  <div style={{ textAlign: 'center', padding: '28px', color: '#94A3B8' }}>
                    No stock movements logged yet for this material.
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                  {(historyData.movements || []).map((mv, idx) => {
                    const qty = Number(mv.quantity) || 0;
                    const isConsume = mv.movement_type === 'manufacturing_consumption';
                    const isIn = qty > 0;
                    return (
                      <div
                        key={mv.id}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '16px 1fr',
                          gap: '12px',
                          paddingBottom: idx === historyData.movements.length - 1 ? 0 : '4px',
                        }}
                      >
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          <div
                            style={{
                              width: '10px',
                              height: '10px',
                              borderRadius: '50%',
                              backgroundColor: isConsume ? '#DC2626' : isIn ? '#059669' : '#D97706',
                              marginTop: '6px',
                              flexShrink: 0,
                            }}
                          />
                          {idx !== historyData.movements.length - 1 && (
                            <div style={{ width: '2px', flex: 1, backgroundColor: '#E2E8F0', minHeight: '28px' }} />
                          )}
                        </div>
                        <div
                          style={{
                            marginBottom: '12px',
                            padding: '10px 12px',
                            borderRadius: '8px',
                            border: '1px solid #E2E8F0',
                            backgroundColor: isConsume ? '#FFF7F7' : '#F8FAFC',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'baseline' }}>
                            <div style={{ fontWeight: '800', fontSize: '0.85rem', color: '#0F172A' }}>
                              {movementLabel(mv.movement_type)}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748B' }}>
                              {mv.created_at ? new Date(mv.created_at).toLocaleString('en-IN') : ''}
                            </div>
                          </div>
                          {isConsume && mv.product_name && (
                            <div style={{ fontSize: '0.8rem', color: '#B91C1C', fontWeight: '600', marginTop: '2px' }}>
                              Finished product: {mv.product_name}
                              {mv.reference_id ? ` · ${mv.reference_id}` : ''}
                            </div>
                          )}
                          <div style={{ fontSize: '0.8rem', color: '#475569', marginTop: '6px' }}>
                            Qty: <strong style={{ color: isIn ? '#047857' : '#B91C1C' }}>{qty > 0 ? '+' : ''}{formatStockQty(qty, mv.unit || historyData.unit)}</strong>
                            {' · '}Balance: {formatStockQty(mv.previous_balance, mv.unit || historyData.unit)} → {formatStockQty(mv.new_balance, mv.unit || historyData.unit)}
                          </div>
                          <div style={{ fontSize: '0.8rem', fontWeight: '700', color: '#0F172A', marginTop: '4px' }}>
                            ₹{Math.abs(Number(mv.amount_display || mv.amount || 0)).toFixed(2)}
                            {Number(mv.unit_cost) > 0 ? ` @ ₹${Number(mv.unit_cost).toFixed(2)}/${mv.unit || historyData.unit}` : ''}
                          </div>
                          {mv.reason && (
                            <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '4px' }}>{mv.reason}</div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
