import React, { useEffect, useState } from 'react';
import { getProducts, getRawMaterials, getRecipes, saveRecipe, getManufacturingLogs, createManufacturingLog, updateManufacturingLog, finalizeManufacturingLog, recordManufacturingOutput, deleteManufacturingLog, updateRawMaterial } from '../api';
import { Factory, Plus, Search, AlertTriangle, CheckCircle2, FlaskConical, BookOpen, Layers, ArrowRight, Calculator, DollarSign, Eye, X, Trash2, Pencil, Save, Play, PackageCheck } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import { getInputUnitOptions, convertQty, formatQty, formatQtyDisplay } from '../unitUtils';

const DEFAULT_CHARGES = [
  { name: 'Labour Charge', amount: '' },
  { name: 'Electricity Charge', amount: '' },
];

const colHeaderStyle = {
  fontSize: '0.7rem',
  fontWeight: '800',
  color: '#64748B',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  marginBottom: '6px',
};

const MFG_STATUS = {
  draft: { label: 'Draft', bg: '#F1F5F9', color: '#475569' },
  completed: { label: 'Completed', bg: '#ECFDF5', color: '#047857' },
  in_progress: { label: 'In Progress', bg: '#EFF6FF', color: '#1D4ED8' },
  cancelled: { label: 'Cancelled', bg: '#FEE2E2', color: '#B91C1C' },
};

export default function Manufacturing() {
  const [activeTab, setActiveTab] = useState('history'); // history → produce → recipes
  const [products, setProducts] = useState([]);
  const [rawMaterials, setRawMaterials] = useState([]);
  const [recipes, setRecipes] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  // Production Form State
  const [selectedProductId, setSelectedProductId] = useState('');
  const [productionQty, setProductionQty] = useState('10');
  const [actualQtyOptional, setActualQtyOptional] = useState('');
  const [batchNumber, setBatchNumber] = useState(`BATCH-${Math.floor(1000 + Math.random() * 9000)}`);
  const [mfgDate, setMfgDate] = useState(new Date().toISOString().split('T')[0]);
  const [expDate, setExpDate] = useState('');
  const [operator, setOperator] = useState('Production Manager');
  const [notes, setNotes] = useState('');
  
  // Overhead Cost State
  const [laborCost, setLaborCost] = useState('0');
  const [packagingCost, setPackagingCost] = useState('0');
  const [otherOverheadCost, setOtherOverheadCost] = useState('0');
  const [updateProductCostPrice, setUpdateProductCostPrice] = useState(true);

  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [shortageError, setShortageError] = useState(null);
  const [editingDraftId, setEditingDraftId] = useState(null);
  const [historyFilter, setHistoryFilter] = useState('all');

  // Modal State for Viewing Log Details
  const [selectedLogDetails, setSelectedLogDetails] = useState(null);
  const [editingLog, setEditingLog] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [savingEdit, setSavingEdit] = useState(false);

  // Record / edit actual output
  const [outputModalLog, setOutputModalLog] = useState(null);
  const [outputActual, setOutputActual] = useState('');
  const [savingOutput, setSavingOutput] = useState(false);

  // Recipe Builder Form State
  const [recipeProdId, setRecipeProdId] = useState('');
  const [yieldQty, setYieldQty] = useState('1');
  const [recipeItems, setRecipeItems] = useState([
    { raw_material: '', quantity_required: '1', input_unit: '', rate: '' }
  ]);
  const [extraCharges, setExtraCharges] = useState(DEFAULT_CHARGES.map((c) => ({ ...c })));
  const [savingRecipe, setSavingRecipe] = useState(false);

  const toast = useToast();

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = () => {
    Promise.all([
      getProducts(),
      getRawMaterials(),
      getRecipes(),
      getManufacturingLogs(),
    ])
      .then(([prodRes, rmRes, recRes, logRes]) => {
        setProducts(prodRes.data.results || prodRes.data);
        setRawMaterials(rmRes.data.results || rmRes.data);
        setRecipes(recRes.data.results || recRes.data);
        setLogs(logRes.data.results || logRes.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  };

  const selectedProduct = products.find((p) => String(p.id) === String(selectedProductId));
  const currentRecipe = recipes.find((r) => String(r.product) === String(selectedProductId));

  // Compute calculated required raw materials & estimated raw material cost for production batch
  const batchScale = selectedProduct && currentRecipe ? Number(productionQty) / (Number(currentRecipe.yield_quantity) || 1) : 0;
  
  let estimatedRawMaterialCost = 0;
  const calculatedRequirements = currentRecipe?.items?.map((item) => {
    const required = Number(item.quantity_required) * batchScale;
    const rm = rawMaterials.find((r) => String(r.id) === String(item.raw_material));
    const available = rm ? Number(rm.current_stock) : 0;
    const purchasePrice = rm ? Number(rm.purchase_price) : 0;
    const itemCost = required * purchasePrice;
    estimatedRawMaterialCost += itemCost;

    const isShortage = available < required;
    return {
      materialId: item.raw_material,
      name: item.raw_material_name || rm?.name,
      unit: item.raw_material_unit || rm?.unit,
      purchasePrice,
      required,
      available,
      itemCost,
      isShortage,
      shortageQty: isShortage ? required - available : 0,
    };
  }) || [];

  const totalOverheads = (Number(laborCost) || 0) + (Number(packagingCost) || 0) + (Number(otherOverheadCost) || 0);
  const totalBatchCost = estimatedRawMaterialCost + totalOverheads;
  const unitCostDivisor = Number(actualQtyOptional) > 0 ? Number(actualQtyOptional) : Number(productionQty);
  const calculatedUnitCost = unitCostDivisor > 0 ? totalBatchCost / unitCostDivisor : 0;
  const previewWastage =
    Number(actualQtyOptional) > 0 && Number(productionQty) > 0
      ? Math.max(0, Number(productionQty) - Number(actualQtyOptional))
      : null;

  const hasShortages = calculatedRequirements.some((r) => r.isShortage);
  const draftCount = logs.filter((l) => l.status === 'draft').length;
  const inProgressCount = logs.filter((l) => l.status === 'in_progress').length;
  const filteredLogs = logs.filter((log) => {
    if (historyFilter === 'draft') return log.status === 'draft';
    if (historyFilter === 'in_progress') return log.status === 'in_progress';
    if (historyFilter === 'completed') return log.status === 'completed';
    return true;
  });

  const buildPayload = () => {
    const payload = {
      product: selectedProductId,
      production_quantity: Number(productionQty),
      batch_number: batchNumber,
      mfg_date: mfgDate,
      exp_date: expDate || null,
      operator,
      labor_cost: Number(laborCost) || 0,
      packaging_cost: Number(packagingCost) || 0,
      other_overhead_cost: Number(otherOverheadCost) || 0,
      update_product_cost_price: updateProductCostPrice,
      notes,
    };
    if (actualQtyOptional !== '' && Number(actualQtyOptional) > 0) {
      payload.actual_quantity = Number(actualQtyOptional);
    }
    return payload;
  };

  const resetProduceForm = () => {
    setEditingDraftId(null);
    setSelectedProductId('');
    setProductionQty('10');
    setActualQtyOptional('');
    setBatchNumber(`BATCH-${Math.floor(1000 + Math.random() * 9000)}`);
    setMfgDate(new Date().toISOString().split('T')[0]);
    setExpDate('');
    setOperator('Production Manager');
    setNotes('');
    setLaborCost('0');
    setPackagingCost('0');
    setOtherOverheadCost('0');
    setUpdateProductCostPrice(true);
    setShortageError(null);
  };

  const loadDraftIntoForm = (log) => {
    setEditingDraftId(log.id);
    setSelectedProductId(String(log.product));
    setProductionQty(String(log.production_quantity));
    setActualQtyOptional(log.actual_quantity != null ? String(log.actual_quantity) : '');
    setBatchNumber(log.batch_number || '');
    setMfgDate(log.mfg_date || new Date().toISOString().split('T')[0]);
    setExpDate(log.exp_date || '');
    setOperator(log.operator || '');
    setNotes(log.notes || '');
    setLaborCost(String(log.labor_cost ?? '0'));
    setPackagingCost(String(log.packaging_cost ?? '0'));
    setOtherOverheadCost(String(log.other_overhead_cost ?? '0'));
    setShortageError(null);
    setActiveTab('produce');
  };

  const handleApiError = (err, fallback) => {
    if (err.response?.data?.shortages) {
      setShortageError(err.response.data.shortages);
      toast.showError('Insufficient Raw Material Stock! Check shortage breakdown below.');
    } else {
      toast.showError(err.response?.data?.error || fallback);
    }
  };

  const handleSaveDraft = (e) => {
    e.preventDefault();
    setShortageError(null);
    if (!selectedProductId) {
      toast.showError('Please select a finished product to save draft.');
      return;
    }
    setSavingDraft(true);
    const payload = { ...buildPayload(), save_as_draft: true };
    const req = editingDraftId
      ? updateManufacturingLog(editingDraftId, payload)
      : createManufacturingLog(payload);
    req
      .then((res) => {
        toast.showSuccess(editingDraftId ? 'Draft batch updated.' : 'Batch saved as draft.');
        if (!editingDraftId && res.data?.id) setEditingDraftId(res.data.id);
        fetchInitialData();
      })
      .catch((err) => handleApiError(err, 'Failed to save draft.'))
      .finally(() => setSavingDraft(false));
  };

  const handleDeleteDraft = (log) => {
    if (!window.confirm(`Delete draft batch ${log.batch_number}?`)) return;
    deleteManufacturingLog(log.id)
      .then(() => {
        toast.showSuccess('Draft deleted.');
        if (editingDraftId === log.id) resetProduceForm();
        fetchInitialData();
      })
      .catch((err) => toast.showError(err.response?.data?.error || 'Failed to delete draft.'));
  };

  const openEditBatch = (log) => {
    if (log.status === 'draft') {
      loadDraftIntoForm(log);
      return;
    }
    setSelectedLogDetails(null);
    setEditingLog(log);
    setEditForm({
      batch_number: log.batch_number || '',
      mfg_date: log.mfg_date || '',
      exp_date: log.exp_date || '',
      operator: log.operator || '',
      notes: log.notes || '',
      labor_cost: String(log.labor_cost ?? '0'),
      packaging_cost: String(log.packaging_cost ?? '0'),
      other_overhead_cost: String(log.other_overhead_cost ?? '0'),
    });
  };

  const handleSaveEdit = (e) => {
    e.preventDefault();
    if (!editingLog) return;
    if (!editForm.batch_number?.trim()) {
      toast.showError('Batch number is required.');
      return;
    }
    setSavingEdit(true);
    updateManufacturingLog(editingLog.id, {
      batch_number: editForm.batch_number.trim(),
      mfg_date: editForm.mfg_date,
      exp_date: editForm.exp_date || null,
      operator: editForm.operator,
      notes: editForm.notes,
      labor_cost: Number(editForm.labor_cost) || 0,
      packaging_cost: Number(editForm.packaging_cost) || 0,
      other_overhead_cost: Number(editForm.other_overhead_cost) || 0,
    })
      .then((res) => {
        toast.showSuccess(`Batch ${editForm.batch_number} updated.`);
        setEditingLog(null);
        setEditForm({});
        fetchInitialData();
        if (selectedLogDetails?.id === editingLog.id) {
          setSelectedLogDetails(res.data);
        }
      })
      .catch((err) => {
        toast.showError(err.response?.data?.error || 'Failed to update batch.');
      })
      .finally(() => setSavingEdit(false));
  };

  const editTotalCost = editingLog
    ? Number(editingLog.raw_material_cost || 0)
      + (Number(editForm.labor_cost) || 0)
      + (Number(editForm.packaging_cost) || 0)
      + (Number(editForm.other_overhead_cost) || 0)
    : 0;
  const editUnitCost = editingLog && Number(editingLog.actual_quantity || editingLog.production_quantity) > 0
    ? editTotalCost / Number(editingLog.actual_quantity || editingLog.production_quantity)
    : 0;

  const handleFinalizeFromHistory = (log) => {
    if (!window.confirm(`Start manufacturing draft ${log.batch_number}? Raw materials will be deducted for the estimated quantity. Finished stock posts after you record actual output.`)) return;
    setSubmitting(true);
    finalizeManufacturingLog(log.id, {
      product: log.product,
      production_quantity: log.production_quantity,
      batch_number: log.batch_number,
      mfg_date: log.mfg_date,
      exp_date: log.exp_date,
      operator: log.operator,
      notes: log.notes,
      labor_cost: log.labor_cost,
      packaging_cost: log.packaging_cost,
      other_overhead_cost: log.other_overhead_cost,
      update_product_cost_price: true,
    })
      .then((res) => {
        const status = res.data?.status;
        toast.showSuccess(
          status === 'completed'
            ? `Batch ${log.batch_number} completed.`
            : `Batch ${log.batch_number} started. Record actual output when production finishes.`
        );
        if (editingDraftId === log.id) resetProduceForm();
        fetchInitialData();
        if (status === 'in_progress') {
          setActiveTab('history');
          setHistoryFilter('in_progress');
        }
      })
      .catch((err) => handleApiError(err, 'Failed to manufacture draft.'))
      .finally(() => setSubmitting(false));
  };

  const openOutputModal = (log) => {
    setOutputModalLog(log);
    setOutputActual(log.actual_quantity != null ? String(log.actual_quantity) : '');
  };

  const handleRecordOutput = (e) => {
    e.preventDefault();
    if (!outputModalLog) return;
    const estimated = Number(outputModalLog.production_quantity);
    const actual = Number(outputActual);
    if (!actual || actual <= 0) {
      toast.showWarning('Enter actual good units after production.');
      return;
    }
    if (actual > estimated) {
      toast.showWarning(`Actual cannot exceed estimated (${estimated}).`);
      return;
    }
    setSavingOutput(true);
    recordManufacturingOutput(outputModalLog.id, {
      actual_quantity: actual,
      update_product_cost_price: true,
    })
      .then(() => {
        const waste = estimated - actual;
        toast.showSuccess(
          `Recorded ${actual} good units` + (waste > 0 ? ` · wastage ${waste}` : '') + `. Finished stock updated.`
        );
        setOutputModalLog(null);
        setSelectedLogDetails(null);
        fetchInitialData();
      })
      .catch((err) => toast.showError(err.response?.data?.error || 'Failed to record actual output.'))
      .finally(() => setSavingOutput(false));
  };

  const handleExecuteProduction = (e) => {
    e.preventDefault();
    setShortageError(null);
    if (!selectedProductId) {
      toast.showError('Please select a finished product to manufacture.');
      return;
    }
    if (!currentRecipe || !currentRecipe.items?.length) {
      toast.showError(`No Bill of Materials (Recipe) defined for ${selectedProduct?.name}. Define a recipe first.`);
      return;
    }
    if (actualQtyOptional !== '' && Number(actualQtyOptional) > Number(productionQty)) {
      toast.showError('Actual quantity cannot exceed estimated quantity.');
      return;
    }

    setSubmitting(true);
    const payload = buildPayload();
    const req = editingDraftId
      ? finalizeManufacturingLog(editingDraftId, payload)
      : createManufacturingLog(payload);
    req
      .then((res) => {
        const status = res.data?.status;
        if (status === 'completed') {
          toast.showSuccess(
            `Manufactured ${res.data.actual_quantity} good units of ${selectedProduct.name} (est. ${productionQty}). Unit Cost: ₹${Number(res.data.unit_cost || calculatedUnitCost).toFixed(2)}.`
          );
        } else {
          toast.showSuccess(
            `Batch started for ${productionQty} estimated units of ${selectedProduct.name}. Raw materials deducted — record actual output when production finishes.`
          );
        }
        resetProduceForm();
        fetchInitialData();
        setActiveTab('history');
        if (status === 'in_progress') setHistoryFilter('in_progress');
      })
      .catch((err) => {
        handleApiError(err, 'Failed to complete manufacturing batch.');
      })
      .finally(() => setSubmitting(false));
  };

  const handleAddRecipeItem = () => {
    setRecipeItems((prev) => [...prev, { raw_material: '', quantity_required: '1', input_unit: '', rate: '' }]);
  };

  const handleRemoveRecipeItem = (index) => {
    setRecipeItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleRecipeItemChange = (index, field, value) => {
    const updated = [...recipeItems];
    updated[index][field] = value;
    if (field === 'raw_material') {
      const rm = rawMaterials.find((r) => String(r.id) === String(value));
      const u = (rm?.unit || '').toLowerCase();
      updated[index].input_unit = ['mg', 'g', 'kg'].includes(u) ? 'mg' : (rm?.unit || '');
      updated[index].rate = rm ? String(rm.purchase_price ?? '0') : '';
    }
    setRecipeItems(updated);
  };

  const handleRecipeRateChange = (index, value) => {
    const updated = [...recipeItems];
    updated[index].rate = value;
    setRecipeItems(updated);
    const rmId = updated[index].raw_material;
    if (!rmId) return;
    const rateNum = Number(value);
    if (!Number.isFinite(rateNum) || rateNum < 0) return;
    setRawMaterials((prev) =>
      prev.map((rm) => (String(rm.id) === String(rmId) ? { ...rm, purchase_price: rateNum } : rm))
    );
  };

  const persistRawMaterialRate = (rmId, rateValue) => {
    if (!rmId) return;
    const rateNum = Number(rateValue);
    if (!Number.isFinite(rateNum) || rateNum < 0) return;
    const rm = rawMaterials.find((r) => String(r.id) === String(rmId));
    if (!rm) return;
    updateRawMaterial(rmId, { ...rm, purchase_price: rateNum })
      .then((res) => {
        setRawMaterials((prev) => prev.map((r) => (String(r.id) === String(rmId) ? { ...r, ...res.data } : r)));
        toast.showSuccess(`Rate updated for ${rm.name}`);
      })
      .catch((err) => {
        toast.showError(err.response?.data?.error || 'Failed to update material rate.');
      });
  };

  const loadRecipeIntoForm = (productId) => {
    const existing = recipes.find((r) => String(r.product) === String(productId));
    if (existing) {
      setYieldQty(String(existing.yield_quantity));
      setRecipeItems(
        existing.items.map((i) => {
          const stockUnit = (i.raw_material_unit || '').toLowerCase();
          const inputUnit = i.input_unit || (['mg', 'g', 'kg'].includes(stockUnit) ? 'mg' : i.raw_material_unit);
          const qtyDisplay = convertQty(Number(i.quantity_required), i.raw_material_unit, inputUnit);
          return {
            raw_material: String(i.raw_material),
            quantity_required: formatQty(qtyDisplay),
            input_unit: inputUnit,
            rate: String(i.raw_material_price ?? ''),
          };
        })
      );
      const charges = (existing.extra_charges || []).map((c) => ({
        name: c.name || '',
        amount: c.amount != null ? String(c.amount) : '',
      }));
      setExtraCharges(charges.length ? charges : DEFAULT_CHARGES.map((c) => ({ ...c })));
    } else {
      setYieldQty('1');
      setRecipeItems([{ raw_material: '', quantity_required: '1', input_unit: '', rate: '' }]);
      setExtraCharges(DEFAULT_CHARGES.map((c) => ({ ...c })));
    }
  };

  const handleAddCharge = () => {
    setExtraCharges((prev) => [...prev, { name: '', amount: '' }]);
  };

  const handleRemoveCharge = (index) => {
    setExtraCharges((prev) => prev.filter((_, i) => i !== index));
  };

  const handleChargeChange = (index, field, value) => {
    const updated = [...extraCharges];
    updated[index][field] = value;
    setExtraCharges(updated);
  };

  const recipeCostPreview = (() => {
    let materialCost = 0;
    const rows = recipeItems.map((item) => {
      const rm = rawMaterials.find((r) => String(r.id) === String(item.raw_material));
      if (!rm) return { ...item, rm: null, qtyStock: 0, amount: 0, rate: 0 };
      const inputUnit = item.input_unit || rm.unit;
      const qtyStock = convertQty(item.quantity_required, inputUnit, rm.unit);
      const rate = item.rate !== '' && item.rate != null
        ? Number(item.rate)
        : Number(rm.purchase_price || 0);
      const amount = qtyStock * rate;
      materialCost += amount;
      return { ...item, rm, inputUnit, qtyStock, rate, amount };
    });
    const chargesTotal = extraCharges.reduce((sum, c) => sum + (Number(c.amount) || 0), 0);
    const total = materialCost + chargesTotal;
    const yieldN = Number(yieldQty) || 0;
    return {
      rows,
      materialCost,
      chargesTotal,
      total,
      unitCost: yieldN > 0 ? total / yieldN : 0,
    };
  })();

  const handleSaveRecipeSubmit = (e) => {
    e.preventDefault();
    if (!recipeProdId) {
      toast.showError('Please select a product for the recipe.');
      return;
    }
    const validItems = recipeItems.filter((i) => i.raw_material && Number(i.quantity_required) > 0);
    if (!validItems.length) {
      toast.showError('Please add at least one valid raw material ingredient.');
      return;
    }

    setSavingRecipe(true);
    saveRecipe({
      product: recipeProdId,
      yield_quantity: Number(yieldQty),
      extra_charges: extraCharges
        .filter((c) => String(c.name || '').trim())
        .map((c) => ({ name: String(c.name).trim(), amount: Number(c.amount) || 0 })),
      items: validItems.map((i) => ({
        raw_material: i.raw_material,
        quantity_required: Number(i.quantity_required),
        input_unit: i.input_unit,
      })),
    })
      .then(() => {
        toast.showSuccess('Bill of Materials (Recipe) saved successfully!');
        setSavingRecipe(false);
        fetchInitialData();
      })
      .catch((err) => {
        setSavingRecipe(false);
        toast.showError(err.response?.data?.error || 'Failed to save recipe.');
      });
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Manufacturing Unit...</div>;
  }

  const completedCount = logs.filter((l) => l.status === 'completed').length;
  const tabDefs = [
    {
      key: 'history',
      step: '1',
      label: 'Batch History & Cost Valuation',
      short: 'Batch List',
      icon: Layers,
      hint: 'View batches, costs, record actual output',
      count: logs.length,
    },
    {
      key: 'produce',
      step: '2',
      label: 'Create Production Batch',
      short: 'New Batch',
      icon: Factory,
      hint: 'Estimate qty, deduct RM, start production',
      count: null,
    },
    {
      key: 'recipes',
      step: '3',
      label: 'Recipe / BOM Manager',
      short: 'Recipes',
      icon: FlaskConical,
      hint: 'Bill of materials for each product',
      count: recipes.length,
    },
  ];

  return (
    <div>
      {/* Page header — title always clear */}
      <div
        style={{
          marginBottom: '20px',
          padding: '20px 22px',
          borderRadius: '14px',
          background: 'linear-gradient(135deg, #ECFDF5 0%, #F0FDFA 45%, #F8FAFC 100%)',
          border: '1px solid #A7F3D0',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '0.7rem', fontWeight: '800', letterSpacing: '0.08em', textTransform: 'uppercase', color: '#047857', marginBottom: '6px' }}>
              Manufacturing
            </div>
            <h1 style={{ fontSize: '1.65rem', fontWeight: '900', color: '#0F172A', margin: 0, letterSpacing: '-0.02em', lineHeight: 1.2 }}>
              Batch History, Production & Costing
            </h1>
            <p style={{ fontSize: '0.9rem', color: '#475569', margin: '8px 0 0', maxWidth: '560px', lineHeight: 1.45 }}>
              Review past batches and costs first, then create a new batch, or manage recipes (BOM).
            </p>
          </div>
          <button
            type="button"
            className="btn-smart btn-primary-smart"
            style={{ backgroundColor: '#059669', height: '42px', padding: '0 18px', fontWeight: '700' }}
            onClick={() => { resetProduceForm(); setActiveTab('produce'); }}
          >
            <Plus size={18} /> New Batch
          </button>
        </div>

        {/* Flow summary chips */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '16px', flexWrap: 'wrap' }}>
          {[
            { label: 'All batches', value: logs.length, color: '#0F172A' },
            { label: 'Awaiting actual', value: inProgressCount, color: '#1D4ED8' },
            { label: 'Drafts', value: draftCount, color: '#475569' },
            { label: 'Completed', value: completedCount, color: '#047857' },
          ].map((s) => (
            <div
              key={s.label}
              style={{
                background: '#FFFFFF',
                border: '1px solid #E2E8F0',
                borderRadius: '10px',
                padding: '8px 14px',
                minWidth: '110px',
              }}
            >
              <div style={{ fontSize: '0.68rem', fontWeight: '700', color: '#94A3B8', textTransform: 'uppercase' }}>{s.label}</div>
              <div style={{ fontSize: '1.25rem', fontWeight: '900', color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Numbered flow tabs — History first */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          gap: '10px',
          marginBottom: '22px',
        }}
      >
        {tabDefs.map((tab) => {
          const Icon = tab.icon;
          const on = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              style={{
                textAlign: 'left',
                cursor: 'pointer',
                borderRadius: '12px',
                padding: '14px 16px',
                border: on ? '2px solid #059669' : '1px solid #E2E8F0',
                background: on ? '#ECFDF5' : '#FFFFFF',
                boxShadow: on ? '0 4px 14px rgba(5, 150, 105, 0.12)' : 'none',
                transition: 'border-color 0.15s, background 0.15s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                <span
                  style={{
                    width: '26px',
                    height: '26px',
                    borderRadius: '50%',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.8rem',
                    fontWeight: '900',
                    background: on ? '#059669' : '#F1F5F9',
                    color: on ? '#FFFFFF' : '#64748B',
                    flexShrink: 0,
                  }}
                >
                  {tab.step}
                </span>
                <Icon size={18} color={on ? '#059669' : '#64748B'} />
                {tab.count != null && (
                  <span
                    style={{
                      marginLeft: 'auto',
                      fontSize: '0.75rem',
                      fontWeight: '800',
                      color: on ? '#047857' : '#64748B',
                      background: on ? '#D1FAE5' : '#F1F5F9',
                      padding: '2px 8px',
                      borderRadius: '999px',
                    }}
                  >
                    {tab.count}
                  </span>
                )}
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: '800', color: on ? '#064E3B' : '#0F172A', lineHeight: 1.25 }}>
                {tab.label}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '4px', lineHeight: 1.35 }}>{tab.hint}</div>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Batch History (default / first) */}
      {activeTab === 'history' && (
        <div className="smart-card" style={{ overflow: 'hidden' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '12px',
              flexWrap: 'wrap',
              padding: '18px 20px',
              borderBottom: '1px solid #E2E8F0',
              background: '#F8FAFC',
            }}
          >
            <div>
              <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: '900', color: '#0F172A' }}>
                Batch History & Cost Valuation
              </h2>
              <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: '#64748B' }}>
                List of all production batches — estimated vs actual, wastage, and unit cost.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {[
                { key: 'all', label: 'All' },
                { key: 'draft', label: `Drafts (${draftCount})` },
                { key: 'in_progress', label: `Awaiting (${inProgressCount})` },
                { key: 'completed', label: 'Completed' },
              ].map((f) => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setHistoryFilter(f.key)}
                  className={`btn-smart ${historyFilter === f.key ? 'btn-primary-smart' : 'btn-outline-smart'}`}
                  style={{
                    backgroundColor: historyFilter === f.key ? '#059669' : undefined,
                    fontSize: '0.78rem',
                    padding: '6px 12px',
                    fontWeight: '700',
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
          <div style={{ overflowX: 'auto' }}>
          <table className="smart-table">
            <thead>
              <tr>
                <th>Mfg ID</th>
                <th>Status</th>
                <th>Finished Product</th>
                <th>Batch Number</th>
                <th>Estimated</th>
                <th>Actual</th>
                <th>Wastage</th>
                <th>Remaining</th>
                <th>RM Cost</th>
                <th>Total Cost</th>
                <th>Unit Cost</th>
                <th>Mfg Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => {
                const st = MFG_STATUS[log.status] || MFG_STATUS.draft;
                const isDraft = log.status === 'draft';
                const isInProgress = log.status === 'in_progress';
                const isCompleted = log.status === 'completed';
                const unitDiv = Number(log.actual_quantity || log.production_quantity || 1);
                return (
                  <tr key={log.id}>
                    <td style={{ fontWeight: '700', color: '#059669' }}>{log.manufacturing_id}</td>
                    <td>
                      <span className="badge-smart" style={{ backgroundColor: st.bg, color: st.color }}>{st.label}</span>
                    </td>
                    <td style={{ fontWeight: '700', color: '#0F172A' }}>{log.product_name}</td>
                    <td><span className="badge-smart" style={{ backgroundColor: '#ECFDF5', color: '#047857' }}>{log.batch_number}</span></td>
                    <td style={{ fontWeight: '800' }}>{Number(log.production_quantity).toFixed(2)}</td>
                    <td style={{ fontWeight: '800', color: log.actual_quantity != null ? '#047857' : '#94A3B8' }}>
                      {log.actual_quantity != null ? Number(log.actual_quantity).toFixed(2) : '—'}
                    </td>
                    <td style={{ fontWeight: '700', color: Number(log.wastage_quantity || 0) > 0 ? '#B45309' : '#94A3B8' }}>
                      {log.actual_quantity != null ? Number(log.wastage_quantity || 0).toFixed(2) : '—'}
                    </td>
                    <td style={{ fontWeight: '800', color: Number(log.remaining_quantity || 0) > 0 ? '#047857' : '#94A3B8' }}>
                      {log.remaining_quantity == null ? '—' : `${Number(log.remaining_quantity).toFixed(2)} left`}
                    </td>
                    <td style={{ color: '#475569' }}>₹{Number(log.raw_material_cost || 0).toFixed(2)}</td>
                    <td style={{ fontWeight: '800', color: '#0F172A' }}>₹{Number(log.total_cost).toFixed(2)}</td>
                    <td style={{ fontWeight: '800', color: '#059669' }}>₹{Number(log.unit_cost || (Number(log.total_cost) / unitDiv)).toFixed(2)}</td>
                    <td style={{ fontSize: '0.8rem', color: '#64748B' }}>{log.mfg_date}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        {isDraft ? (
                          <>
                            <button
                              onClick={() => loadDraftIntoForm(log)}
                              className="btn-smart btn-outline-smart"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', color: '#059669', borderColor: '#059669' }}
                            >
                              <Pencil size={14} /> Continue
                            </button>
                            <button
                              onClick={() => handleFinalizeFromHistory(log)}
                              className="btn-smart btn-primary-smart"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: '#059669' }}
                            >
                              <Play size={14} /> Manufacture
                            </button>
                            <button
                              onClick={() => handleDeleteDraft(log)}
                              className="btn-smart btn-outline-smart"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', color: '#DC2626', borderColor: '#FCA5A5' }}
                            >
                              <Trash2 size={14} /> Delete
                            </button>
                          </>
                        ) : (
                          <>
                            {(isInProgress || isCompleted) && (
                              <button
                                onClick={() => openOutputModal(log)}
                                className="btn-smart btn-primary-smart"
                                style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: isInProgress ? '#D97706' : '#059669' }}
                              >
                                <PackageCheck size={14} /> {isInProgress ? 'Record actual' : 'Edit actual'}
                              </button>
                            )}
                            <button
                              onClick={() => setSelectedLogDetails(log)}
                              className="btn-smart btn-outline-smart"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                            >
                              <Eye size={14} /> View
                            </button>
                            <button
                              onClick={() => openEditBatch(log)}
                              className="btn-smart btn-outline-smart"
                              style={{ padding: '4px 8px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', color: '#059669', borderColor: '#059669' }}
                            >
                              <Pencil size={14} /> Edit
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filteredLogs.length === 0 && (
                <tr>
                  <td colSpan="13" style={{ textAlign: 'center', padding: '32px', color: '#94A3B8' }}>
                    {historyFilter === 'draft' ? 'No draft batches saved yet.' : historyFilter === 'in_progress' ? 'No batches awaiting actual output.' : 'No manufacturing batches logged yet.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {/* Tab 2: Create Production Batch */}
      {activeTab === 'produce' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px' }}>
          <div className="smart-card" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: '900', marginBottom: '6px', color: '#0F172A', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Factory size={20} color="#059669" /> {editingDraftId ? 'Edit Draft Batch' : 'Create Production Batch'}
            </h2>
            <p style={{ fontSize: '0.8rem', color: '#64748B', marginBottom: '16px' }}>
              Enter estimated quantity to deduct raw materials. Record actual output after production finishes.
            </p>
            {editingDraftId && (
              <div style={{ marginBottom: '16px', padding: '12px 14px', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ fontSize: '0.85rem', color: '#92400E' }}>
                  <strong>Draft mode</strong> — stock is not consumed until you confirm manufacturing.
                </div>
                <button type="button" className="btn-smart btn-outline-smart" style={{ fontSize: '0.75rem', padding: '4px 10px' }} onClick={resetProduceForm}>
                  Cancel draft
                </button>
              </div>
            )}
            <form onSubmit={handleExecuteProduction}>
              <div style={{ marginBottom: '16px' }}>
                <label className="pos-field-label">SELECT FINISHED AYURVEDIC PRODUCT *</label>
                <select
                  required
                  className="form-control-smart"
                  value={selectedProductId}
                  onChange={(e) => {
                    setSelectedProductId(e.target.value);
                    setShortageError(null);
                    const existing = recipes.find((r) => String(r.product) === String(e.target.value));
                    const scale = existing ? Number(productionQty) / (Number(existing.yield_quantity) || 1) : 1;
                    let labor = 0;
                    let pack = 0;
                    let other = 0;
                    (existing?.extra_charges || []).forEach((c) => {
                      const label = String(c.name || '').toLowerCase();
                      const amt = (Number(c.amount) || 0) * scale;
                      if (/labour|labor|wage/.test(label)) labor += amt;
                      else if (/packag/.test(label)) pack += amt;
                      else other += amt;
                    });
                    if (existing?.extra_charges?.length) {
                      setLaborCost(String(labor));
                      setPackagingCost(String(pack));
                      setOtherOverheadCost(String(other));
                    }
                  }}
                >
                  <option value="">Select Product...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} (SKU: {p.sku}) — Stock: {p.stock?.quantity ?? 0} {p.uom} (Current Cost: ₹{Number(p.cost_price).toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label className="pos-field-label">ESTIMATED QUANTITY (UNITS) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    className="form-control-smart"
                    value={productionQty}
                    onChange={(e) => setProductionQty(e.target.value)}
                  />
                  <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>
                    Raw materials are deducted for this estimate.
                  </div>
                </div>
                <div>
                  <label className="pos-field-label">BATCH NUMBER *</label>
                  <input
                    type="text"
                    required
                    className="form-control-smart"
                    value={batchNumber}
                    onChange={(e) => setBatchNumber(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label className="pos-field-label">ACTUAL AFTER PRODUCTION (OPTIONAL)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  className="form-control-smart"
                  value={actualQtyOptional}
                  onChange={(e) => setActualQtyOptional(e.target.value)}
                  placeholder="Leave blank — record later when production finishes"
                />
                <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>
                  Finished stock posts from actual only. Wastage = estimated − actual
                  {previewWastage != null ? ` → ${previewWastage}` : ''}.
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label className="pos-field-label">MANUFACTURING DATE</label>
                  <input
                    type="date"
                    required
                    className="form-control-smart"
                    value={mfgDate}
                    onChange={(e) => setMfgDate(e.target.value)}
                  />
                </div>
                <div>
                  <label className="pos-field-label">EXPIRY DATE (OPTIONAL)</label>
                  <input
                    type="date"
                    className="form-control-smart"
                    value={expDate}
                    onChange={(e) => setExpDate(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label className="pos-field-label">OPERATOR / SUPERVISOR</label>
                <input
                  type="text"
                  className="form-control-smart"
                  value={operator}
                  onChange={(e) => setOperator(e.target.value)}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label className="pos-field-label">BATCH NOTES (OPTIONAL)</label>
                <textarea
                  className="form-control-smart"
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Any production remarks…"
                />
              </div>

              {/* OVERHEAD COSTING SECTION */}
              <div style={{ padding: '16px', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '10px', marginBottom: '20px' }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: '800', color: '#1E293B', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Calculator size={16} color="#059669" /> Batch Overhead Expenses (₹)
                </h3>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                  <div>
                    <label className="pos-field-label">LABOR & WAGES (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      className="form-control-smart"
                      value={laborCost}
                      onChange={(e) => setLaborCost(e.target.value)}
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="pos-field-label">PACKAGING / BOTTLES (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      className="form-control-smart"
                      value={packagingCost}
                      onChange={(e) => setPackagingCost(e.target.value)}
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="pos-field-label">ELECTRICITY / OVERHEADS (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      className="form-control-smart"
                      value={otherOverheadCost}
                      onChange={(e) => setOtherOverheadCost(e.target.value)}
                      placeholder="0.00"
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
                  <input
                    type="checkbox"
                    id="updateCostPrice"
                    checked={updateProductCostPrice}
                    onChange={(e) => setUpdateProductCostPrice(e.target.checked)}
                    style={{ accentColor: '#059669', width: '16px', height: '16px' }}
                  />
                  <label htmlFor="updateCostPrice" style={{ fontSize: '0.8rem', color: '#334155', fontWeight: '600', cursor: 'pointer' }}>
                    Auto-update product master Cost Price to calculated batch unit cost (₹{calculatedUnitCost.toFixed(2)}/unit)
                  </label>
                </div>
              </div>

              {shortageError && (
                <div style={{ backgroundColor: '#FEE2E2', border: '1px solid #FCA5A5', padding: '16px', borderRadius: '10px', marginBottom: '20px', color: '#991B1B' }}>
                  <div style={{ fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <AlertTriangle size={18} /> INSUFFICIENT RAW MATERIAL STOCK!
                  </div>
                  <ul style={{ paddingLeft: '20px', fontSize: '0.85rem' }}>
                    {shortageError.map((s, idx) => (
                      <li key={idx}>
                        <strong>{s.material}</strong>: Required {formatQtyDisplay(s.required, s.unit)}, Available {formatQtyDisplay(s.available, s.unit)} (Shortage: {formatQtyDisplay(s.shortage, s.unit)})
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  disabled={savingDraft || submitting || !selectedProductId}
                  onClick={handleSaveDraft}
                  className="btn-smart btn-outline-smart"
                  style={{ flex: 1, minWidth: '160px', height: '44px', fontSize: '0.9rem' }}
                >
                  <Save size={16} /> {savingDraft ? 'Saving draft…' : editingDraftId ? 'Update draft' : 'Save draft'}
                </button>
                <button
                  type="submit"
                  disabled={submitting || savingDraft || hasShortages || !selectedProductId || !currentRecipe?.items?.length}
                  className="btn-smart btn-primary-smart"
                  style={{ flex: 2, minWidth: '220px', height: '44px', backgroundColor: hasShortages || !currentRecipe?.items?.length ? '#94A3B8' : '#059669', fontSize: '0.9rem' }}
                >
                  <Play size={16} /> {submitting ? 'Processing…' : editingDraftId ? 'Confirm & manufacture draft' : `Confirm & manufacture (₹${totalBatchCost.toFixed(2)})`}
                </button>
              </div>
            </form>
          </div>

          {/* BOM Calculation & Cost Breakdown Preview */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Live Costing Summary Card */}
            <div className="smart-card" style={{ padding: '20px', background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 100%)', color: '#FFFFFF' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94A3B8', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <DollarSign size={16} color="#10B981" /> Live Batch Cost Valuation
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div style={{ backgroundColor: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94A3B8' }}>Est. Raw Material Cost</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#38BDF8' }}>₹{estimatedRawMaterialCost.toFixed(2)}</div>
                </div>
                <div style={{ backgroundColor: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94A3B8' }}>Total Overhead Expenses</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#FBBF24' }}>₹{totalOverheads.toFixed(2)}</div>
                </div>
              </div>

              <div style={{ borderTop: '1px dashed rgba(255,255,255,0.15)', paddingTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94A3B8' }}>TOTAL BATCH PRODUCTION COST</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: '900', color: '#10B981' }}>₹{totalBatchCost.toFixed(2)}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94A3B8' }}>
                    UNIT COST {Number(actualQtyOptional) > 0 ? '(on actual)' : '(est. until actual)'}
                  </div>
                  <div style={{ fontSize: '1.3rem', fontWeight: '900', color: '#F43F5E', backgroundColor: 'rgba(244, 63, 94, 0.15)', padding: '4px 10px', borderRadius: '6px' }}>
                    ₹{calculatedUnitCost.toFixed(2)} <span style={{ fontSize: '0.7rem' }}>/ unit</span>
                  </div>
                </div>
              </div>
              <div style={{ marginTop: '12px', fontSize: '0.72rem', color: '#94A3B8', lineHeight: 1.4 }}>
                RM scale uses estimated qty. Finished stock is posted only when actual output is recorded.
              </div>
            </div>

            {/* Raw Material Breakdown List */}
            <div className="smart-card" style={{ padding: '20px' }}>
              <h2 style={{ fontSize: '1rem', fontWeight: '800', marginBottom: '12px', color: '#0F172A' }}>
                Required Raw Material Ingredients
              </h2>
              {!selectedProduct ? (
                <p style={{ color: '#64748B', fontSize: '0.85rem' }}>Select a finished product on the left to inspect raw material consumption & cost.</p>
              ) : !currentRecipe ? (
                <div style={{ padding: '16px', backgroundColor: '#FEF3C7', borderRadius: '10px', color: '#92400E' }}>
                  <AlertTriangle size={20} style={{ marginBottom: '6px' }} />
                  <div style={{ fontWeight: '700' }}>No Recipe (BOM) Found!</div>
                  <p style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                    Please switch to the <strong>Recipe / BOM Manager</strong> tab to set up ingredients for "{selectedProduct.name}".
                  </p>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: '0.8rem', color: '#64748B', marginBottom: '12px' }}>
                    Recipe Yield: <strong>{currentRecipe.yield_quantity} units</strong> · Estimated Batch: <strong>{productionQty} units</strong>
                    {Number(actualQtyOptional) > 0 && <> · Actual: <strong>{actualQtyOptional}</strong></>}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {calculatedRequirements.map((req, i) => (
                      <div
                        key={i}
                        style={{
                          padding: '10px 12px',
                          borderRadius: '8px',
                          border: req.isShortage ? '1px solid #FCA5A5' : '1px solid #E2E8F0',
                          backgroundColor: req.isShortage ? '#FEF2F2' : '#F8FAFC',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: '700', color: '#0F172A', fontSize: '0.85rem' }}>{req.name}</div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px', flexWrap: 'wrap' }}>
                            <label style={{ fontSize: '0.75rem', color: '#64748B', fontWeight: '600' }}>Rate ₹</label>
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              className="form-control-smart"
                              style={{ width: '100px', padding: '4px 8px', fontSize: '0.8rem' }}
                              value={rawMaterials.find((r) => String(r.id) === String(req.materialId))?.purchase_price ?? ''}
                              onChange={(e) => {
                                setRawMaterials((prev) =>
                                  prev.map((rm) =>
                                    String(rm.id) === String(req.materialId)
                                      ? { ...rm, purchase_price: e.target.value }
                                      : rm
                                  )
                                );
                              }}
                              onBlur={(e) => persistRawMaterialRate(req.materialId, e.target.value)}
                              title={`Purchase rate per ${req.unit}`}
                            />
                            <span style={{ fontSize: '0.75rem', color: '#64748B' }}>
                              / {req.unit} · Avail: {req.available.toFixed(2)} {req.unit}
                            </span>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontWeight: '800', color: req.isShortage ? '#DC2626' : '#059669', fontSize: '0.9rem' }}>
                            {formatQtyDisplay(req.required, req.unit)}
                          </div>
                          <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#475569' }}>
                            = ₹{req.itemCost.toFixed(2)}
                          </div>
                          {req.isShortage && (
                            <span style={{ fontSize: '0.7rem', color: '#DC2626', fontWeight: '700' }}>
                              Shortage: {formatQtyDisplay(req.shortageQty, req.unit)}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Recipe / BOM Manager */}
      {activeTab === 'recipes' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 0.9fr', gap: '24px', alignItems: 'start' }}>
          <div className="smart-card" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: '900', marginBottom: '6px', color: '#0F172A', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FlaskConical size={20} color="#059669" /> Recipe / BOM Manager
            </h2>
            <p style={{ fontSize: '0.8rem', color: '#64748B', marginBottom: '16px' }}>
              Define raw materials and yield for each finished product before manufacturing.
            </p>
            <form onSubmit={handleSaveRecipeSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', marginBottom: '20px' }}>
                <div>
                  <label className="pos-field-label">Finished Product *</label>
                  <select
                    required
                    className="form-control-smart"
                    value={recipeProdId}
                    onChange={(e) => {
                      setRecipeProdId(e.target.value);
                      loadRecipeIntoForm(e.target.value);
                    }}
                  >
                    <option value="">Select Product...</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} (SKU: {p.sku})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="pos-field-label">Recipe Yield (units produced) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    className="form-control-smart"
                    value={yieldQty}
                    onChange={(e) => setYieldQty(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label className="pos-field-label" style={{ marginBottom: 0 }}>Raw Material Ingredients</label>
                  <button type="button" onClick={handleAddRecipeItem} className="btn-smart btn-outline-smart" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                    <Plus size={14} /> Add Ingredient Row
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2.2fr 0.9fr 0.9fr 0.9fr 0.9fr 40px', gap: '8px', marginBottom: '6px', padding: '0 0 4px' }}>
                  <div style={colHeaderStyle}>Ingredient</div>
                  <div style={colHeaderStyle}>Quantity</div>
                  <div style={colHeaderStyle}>Unit (mg/g…)</div>
                  <div style={colHeaderStyle}>Rate</div>
                  <div style={colHeaderStyle}>Amount (₹)</div>
                  <div />
                </div>
                <p style={{ fontSize: '0.75rem', color: '#64748B', marginBottom: '12px' }}>
                  Enter medicine quantities in <strong>mg</strong> (milligram). Stock is converted automatically to your material&apos;s unit (g/kg).
                </p>

                {recipeItems.map((item, idx) => {
                  const row = recipeCostPreview.rows[idx];
                  const rm = row?.rm;
                  const unitOptions = getInputUnitOptions(rm?.unit);
                  return (
                    <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2.2fr 0.9fr 0.9fr 0.9fr 0.9fr 40px', gap: '8px', alignItems: 'start', marginBottom: '10px' }}>
                      <select
                        className="form-control-smart"
                        value={item.raw_material}
                        onChange={(e) => handleRecipeItemChange(idx, 'raw_material', e.target.value)}
                      >
                        <option value="">Select raw material...</option>
                        {rawMaterials.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name} ({m.category})
                          </option>
                        ))}
                      </select>
                      <div>
                        <input
                          type="number"
                          step="any"
                          min="0"
                          placeholder="Qty"
                          className="form-control-smart"
                          value={item.quantity_required}
                          onChange={(e) => handleRecipeItemChange(idx, 'quantity_required', e.target.value)}
                        />
                        {rm && item.input_unit && item.input_unit !== rm.unit && (
                          <div style={{ fontSize: '0.68rem', color: '#64748B', marginTop: '4px' }}>
                            = {formatQty(row.qtyStock)} {rm.unit}
                          </div>
                        )}
                      </div>
                      <select
                        className="form-control-smart"
                        value={item.input_unit || rm?.unit || ''}
                        disabled={!rm}
                        onChange={(e) => handleRecipeItemChange(idx, 'input_unit', e.target.value)}
                      >
                        {!rm && <option value="">Unit</option>}
                        {unitOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                      <div>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          className="form-control-smart"
                          placeholder="Rate"
                          value={item.rate !== undefined && item.rate !== '' ? item.rate : (rm ? String(rm.purchase_price ?? '') : '')}
                          disabled={!rm}
                          onChange={(e) => handleRecipeRateChange(idx, e.target.value)}
                          onBlur={(e) => persistRawMaterialRate(item.raw_material, e.target.value)}
                          title={rm ? `Purchase rate per ${rm.unit}` : ''}
                        />
                        {rm && (
                          <div style={{ fontSize: '0.68rem', color: '#64748B', marginTop: '4px' }}>
                            / {rm.unit}
                          </div>
                        )}
                      </div>
                      <div style={{ fontSize: '0.9rem', color: '#059669', paddingTop: '10px', fontWeight: '800' }}>
                        {rm ? `₹${row.amount.toFixed(2)}` : '—'}
                      </div>
                      {recipeItems.length > 1 ? (
                        <button type="button" onClick={() => handleRemoveRecipeItem(idx)} className="btn-smart btn-outline-smart" style={{ color: '#DC2626', padding: '8px' }}>
                          <Trash2 size={14} />
                        </button>
                      ) : (
                        <div />
                      )}
                    </div>
                  );
                })}
              </div>

              <div style={{ marginBottom: '20px', padding: '16px', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <label className="pos-field-label" style={{ marginBottom: 0 }}>Additional Charges (Labour, Electricity, etc.)</label>
                  <button type="button" onClick={handleAddCharge} className="btn-smart btn-outline-smart" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                    <Plus size={14} /> Add Charge
                  </button>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 40px', gap: '8px', marginBottom: '6px' }}>
                  <div style={colHeaderStyle}>Charge name</div>
                  <div style={colHeaderStyle}>Amount (₹)</div>
                  <div />
                </div>
                {extraCharges.map((charge, idx) => (
                  <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 40px', gap: '8px', marginBottom: '8px' }}>
                    <input
                      type="text"
                      className="form-control-smart"
                      placeholder="e.g. Labour Charge, Electricity, Packaging"
                      value={charge.name}
                      onChange={(e) => handleChargeChange(idx, 'name', e.target.value)}
                    />
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      className="form-control-smart"
                      placeholder="0.00"
                      value={charge.amount}
                      onChange={(e) => handleChargeChange(idx, 'amount', e.target.value)}
                    />
                    {extraCharges.length > 1 ? (
                      <button type="button" onClick={() => handleRemoveCharge(idx)} className="btn-smart btn-outline-smart" style={{ color: '#DC2626', padding: '8px' }}>
                        <Trash2 size={14} />
                      </button>
                    ) : (
                      <div />
                    )}
                  </div>
                ))}
                <p style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '4px' }}>
                  Add any cost that applies to this recipe yield — labour, electricity, fuel, packaging, or a custom charge.
                </p>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button type="submit" disabled={savingRecipe || !recipeProdId} className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }}>
                  {savingRecipe ? 'Saving Recipe...' : 'Save Recipe / BOM'}
                </button>
              </div>
            </form>
          </div>

          <div className="smart-card" style={{ padding: '20px', background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 100%)', color: '#FFFFFF' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94A3B8', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <DollarSign size={16} color="#10B981" /> Recipe Cost Summary
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontSize: '0.85rem' }}>
              <span style={{ color: '#94A3B8' }}>Raw materials</span>
              <span style={{ fontWeight: '700' }}>₹{recipeCostPreview.materialCost.toFixed(2)}</span>
            </div>
            {extraCharges.filter((c) => String(c.name || '').trim()).map((c, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.85rem' }}>
                <span style={{ color: '#94A3B8' }}>{c.name}</span>
                <span style={{ fontWeight: '700', color: '#FBBF24' }}>₹{(Number(c.amount) || 0).toFixed(2)}</span>
              </div>
            ))}
            <div style={{ borderTop: '1px dashed rgba(255,255,255,0.15)', paddingTop: '12px', marginTop: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94A3B8' }}>TOTAL COST FOR {yieldQty || 0} UNIT(S)</div>
              <div style={{ fontSize: '1.5rem', fontWeight: '900', color: '#10B981' }}>₹{recipeCostPreview.total.toFixed(2)}</div>
              <div style={{ marginTop: '10px', fontSize: '0.75rem', color: '#94A3B8' }}>COST PER FINISHED UNIT</div>
              <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#F43F5E' }}>₹{recipeCostPreview.unitCost.toFixed(2)}</div>
            </div>
          </div>
        </div>
      )}

      {/* Batch Details Modal */}
      {selectedLogDetails && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)',
          display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
        }}>
          <div className="smart-card" style={{ width: '90%', maxWidth: '650px', maxHeight: '90vh', overflowY: 'auto', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #E2E8F0', pb: '12px' }}>
              <div>
                <h2 style={{ fontSize: '1.2rem', fontWeight: '800', color: '#0F172A' }}>
                  Batch Details: {selectedLogDetails.manufacturing_id}
                </h2>
                <div style={{ fontSize: '0.85rem', color: '#64748B' }}>
                  {selectedLogDetails.product_name} · Batch #{selectedLogDetails.batch_number}
                </div>
              </div>
              <button onClick={() => setSelectedLogDetails(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#64748B' }}>
                <X size={20} />
              </button>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '12px', gap: '8px' }}>
              {(selectedLogDetails.status === 'in_progress' || selectedLogDetails.status === 'completed') && (
                <button
                  type="button"
                  onClick={() => openOutputModal(selectedLogDetails)}
                  className="btn-smart btn-primary-smart"
                  style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px', backgroundColor: selectedLogDetails.status === 'in_progress' ? '#D97706' : '#059669' }}
                >
                  <PackageCheck size={14} /> {selectedLogDetails.status === 'in_progress' ? 'Record actual' : 'Edit actual'}
                </button>
              )}
              <button
                type="button"
                onClick={() => openEditBatch(selectedLogDetails)}
                className="btn-smart btn-outline-smart"
                style={{ padding: '6px 12px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px', color: '#059669', borderColor: '#059669' }}
              >
                <Pencil size={14} /> Edit Batch
              </button>
            </div>

            {/* Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '20px' }}>
              <div style={{ padding: '12px', backgroundColor: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748B' }}>Estimated / Actual / Wastage</div>
                <div style={{ fontSize: '1.05rem', fontWeight: '800', color: '#0F172A' }}>
                  {selectedLogDetails.production_quantity}
                  {' / '}
                  {selectedLogDetails.actual_quantity != null ? selectedLogDetails.actual_quantity : '—'}
                  {' / '}
                  <span style={{ color: '#B45309' }}>
                    {selectedLogDetails.actual_quantity != null ? Number(selectedLogDetails.wastage_quantity || 0).toFixed(2) : '—'}
                  </span>
                </div>
                {selectedLogDetails.remaining_quantity != null && (
                  <div style={{ fontSize: '0.75rem', color: '#047857', marginTop: '4px', fontWeight: '700' }}>
                    {Number(selectedLogDetails.remaining_quantity).toFixed(2)} still left in this batch
                  </div>
                )}
              </div>
              <div style={{ padding: '12px', backgroundColor: '#ECFDF5', borderRadius: '8px', border: '1px solid #A7F3D0' }}>
                <div style={{ fontSize: '0.75rem', color: '#047857' }}>Total Batch Cost</div>
                <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#065F46' }}>₹{Number(selectedLogDetails.total_cost).toFixed(2)}</div>
              </div>
              <div style={{ padding: '12px', backgroundColor: '#EFF6FF', borderRadius: '8px', border: '1px solid #BFDBFE' }}>
                <div style={{ fontSize: '0.75rem', color: '#1D4ED8' }}>Unit Production Cost</div>
                <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#1E40AF' }}>₹{Number(selectedLogDetails.unit_cost || 0).toFixed(2)}</div>
              </div>
            </div>

            {/* Cost Breakdown */}
            <h3 style={{ fontSize: '0.9rem', fontWeight: '700', marginBottom: '10px', color: '#334155' }}>Overhead Breakdown</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '10px', marginBottom: '20px', fontSize: '0.85rem' }}>
              <div style={{ background: '#F8FAFC', padding: '10px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748B' }}>Raw Materials</div>
                <div style={{ fontWeight: '700', color: '#0F172A' }}>₹{Number(selectedLogDetails.raw_material_cost || 0).toFixed(2)}</div>
              </div>
              <div style={{ background: '#F8FAFC', padding: '10px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748B' }}>Labor / Wages</div>
                <div style={{ fontWeight: '700', color: '#0F172A' }}>₹{Number(selectedLogDetails.labor_cost || 0).toFixed(2)}</div>
              </div>
              <div style={{ background: '#F8FAFC', padding: '10px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748B' }}>Packaging</div>
                <div style={{ fontWeight: '700', color: '#0F172A' }}>₹{Number(selectedLogDetails.packaging_cost || 0).toFixed(2)}</div>
              </div>
              <div style={{ background: '#F8FAFC', padding: '10px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748B' }}>Electricity/Overheads</div>
                <div style={{ fontWeight: '700', color: '#0F172A' }}>₹{Number(selectedLogDetails.other_overhead_cost || 0).toFixed(2)}</div>
              </div>
            </div>

            {/* Consumed Raw Material Table */}
            <h3 style={{ fontSize: '0.9rem', fontWeight: '700', marginBottom: '10px', color: '#334155' }}>Consumed Ingredients</h3>
            <table className="smart-table" style={{ fontSize: '0.85rem' }}>
              <thead>
                <tr>
                  <th>Raw Material</th>
                  <th>Consumed Qty</th>
                  <th>Purchase Rate</th>
                  <th>Total Item Cost</th>
                </tr>
              </thead>
              <tbody>
                {selectedLogDetails.consumed_items?.map((item) => (
                  <tr key={item.id}>
                    <td style={{ fontWeight: '600' }}>{item.raw_material_name}</td>
                    <td>{formatQtyDisplay(item.quantity_consumed, item.raw_material_unit)}</td>
                    <td>₹{Number(item.unit_cost).toFixed(2)}</td>
                    <td style={{ fontWeight: '700', color: '#059669' }}>₹{Number(item.total_cost).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Batch Modal */}
      {editingLog && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)',
          display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
        }}>
          <div className="smart-card" style={{ width: '90%', maxWidth: '560px', maxHeight: '90vh', overflowY: 'auto', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #E2E8F0', paddingBottom: '12px' }}>
              <div>
                <h2 style={{ fontSize: '1.2rem', fontWeight: '800', color: '#0F172A', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Pencil size={20} color="#059669" /> Edit Batch
                </h2>
                <div style={{ fontSize: '0.85rem', color: '#64748B' }}>
                  {editingLog.manufacturing_id} · {editingLog.product_name} · {Number(editingLog.production_quantity).toFixed(2)} units produced
                </div>
              </div>
              <button type="button" onClick={() => { setEditingLog(null); setEditForm({}); }} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#64748B' }}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveEdit}>
              <div className="form-field">
                <label className="form-field-label" htmlFor="edit-batch-no">Batch Number *</label>
                <input id="edit-batch-no" type="text" className="form-control-smart" required value={editForm.batch_number} onChange={(e) => setEditForm({ ...editForm, batch_number: e.target.value })} />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-field">
                  <label className="form-field-label" htmlFor="edit-mfg-date">Manufacturing Date</label>
                  <input id="edit-mfg-date" type="date" className="form-control-smart" required value={editForm.mfg_date} onChange={(e) => setEditForm({ ...editForm, mfg_date: e.target.value })} />
                </div>
                <div className="form-field">
                  <label className="form-field-label" htmlFor="edit-exp-date">Expiry Date</label>
                  <input id="edit-exp-date" type="date" className="form-control-smart" value={editForm.exp_date} onChange={(e) => setEditForm({ ...editForm, exp_date: e.target.value })} />
                </div>
              </div>

              <div className="form-field">
                <label className="form-field-label" htmlFor="edit-operator">Operator / Supervisor</label>
                <input id="edit-operator" type="text" className="form-control-smart" value={editForm.operator} onChange={(e) => setEditForm({ ...editForm, operator: e.target.value })} />
              </div>

              <div style={{ padding: '14px', background: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0', marginBottom: '12px' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: '800', color: '#64748B', marginBottom: '10px', textTransform: 'uppercase' }}>Overhead Expenses (₹)</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: '#64748B', display: 'block', marginBottom: '4px' }}>Labor</label>
                    <input type="number" step="0.01" min="0" className="form-control-smart" value={editForm.labor_cost} onChange={(e) => setEditForm({ ...editForm, labor_cost: e.target.value })} />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: '#64748B', display: 'block', marginBottom: '4px' }}>Packaging</label>
                    <input type="number" step="0.01" min="0" className="form-control-smart" value={editForm.packaging_cost} onChange={(e) => setEditForm({ ...editForm, packaging_cost: e.target.value })} />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: '#64748B', display: 'block', marginBottom: '4px' }}>Other</label>
                    <input type="number" step="0.01" min="0" className="form-control-smart" value={editForm.other_overhead_cost} onChange={(e) => setEditForm({ ...editForm, other_overhead_cost: e.target.value })} />
                  </div>
                </div>
                <div style={{ marginTop: '12px', fontSize: '0.85rem', color: '#475569' }}>
                  Raw material cost (fixed): <strong>₹{Number(editingLog.raw_material_cost || 0).toFixed(2)}</strong>
                  {' · '}
                  Updated total: <strong style={{ color: '#059669' }}>₹{editTotalCost.toFixed(2)}</strong>
                  {' · '}
                  Unit cost: <strong>₹{editUnitCost.toFixed(2)}</strong>
                </div>
              </div>

              <div className="form-field" style={{ marginBottom: '20px' }}>
                <label className="form-field-label" htmlFor="edit-notes">Notes</label>
                <textarea id="edit-notes" className="form-control-smart" rows="2" value={editForm.notes} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn-smart btn-secondary-smart" onClick={() => { setEditingLog(null); setEditForm({}); }}>
                  Cancel
                </button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }} disabled={savingEdit}>
                  {savingEdit ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {outputModalLog && (
        <div
          className="modal-backdrop"
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)',
            display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1100,
          }}
          onClick={() => !savingOutput && setOutputModalLog(null)}
        >
          <div
            className="smart-card"
            style={{ width: '92%', maxWidth: '440px', padding: '24px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: '800', color: '#0F172A', margin: 0 }}>
                  {outputModalLog.status === 'completed' ? 'Edit actual output' : 'Record actual output'}
                </h2>
                <p style={{ fontSize: '0.8rem', color: '#64748B', margin: '4px 0 0' }}>
                  {outputModalLog.product_name} · {outputModalLog.batch_number}
                </p>
              </div>
              <button type="button" onClick={() => setOutputModalLog(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#94A3B8' }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ padding: '12px', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '8px', marginBottom: '16px', fontSize: '0.85rem', color: '#92400E' }}>
              Estimated (RM already deducted): <strong>{Number(outputModalLog.production_quantity).toFixed(2)}</strong> units.
              Finished stock will use the actual count you enter below.
            </div>

            <form onSubmit={handleRecordOutput}>
              <div style={{ marginBottom: '12px' }}>
                <label className="pos-field-label">Actual good units *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={Number(outputModalLog.production_quantity)}
                  required
                  className="form-control-smart"
                  value={outputActual}
                  onChange={(e) => setOutputActual(e.target.value)}
                  autoFocus
                />
              </div>
              <div style={{ marginBottom: '18px', fontSize: '0.85rem', color: '#475569' }}>
                Wastage:{' '}
                <strong style={{ color: '#B45309' }}>
                  {outputActual && Number(outputActual) > 0
                    ? Math.max(0, Number(outputModalLog.production_quantity) - Number(outputActual)).toFixed(2)
                    : '—'}
                </strong>
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn-smart btn-secondary-smart" disabled={savingOutput} onClick={() => setOutputModalLog(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#D97706', borderColor: '#D97706' }} disabled={savingOutput}>
                  {savingOutput ? 'Saving…' : 'Save actual output'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
