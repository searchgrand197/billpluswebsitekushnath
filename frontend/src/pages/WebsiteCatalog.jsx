import React, { useEffect, useState } from 'react';
import {
  getWebsiteProducts,
  getWebsiteCategories,
  createWebsiteProduct,
  updateWebsiteProduct,
  deleteWebsiteProduct,
  createWebsiteCategory,
  updateWebsiteCategory,
  deleteWebsiteCategory,
  uploadWebsiteProductImage,
  deleteWebsiteProductImage,
  mediaUrl,
} from '../websiteApi';
import { Globe, Plus, Pencil, Trash2, Search, ImagePlus, X, Package } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import ConfirmationModal from '../components/ConfirmationModal';

const emptyProduct = {
  name: '',
  sku: '',
  category_id: '',
  quantity: '1 unit',
  stock: '0',
  price: '',
  discount_type: 'percent',
  discount: '0',
  description: '',
  weight: '',
  length: '',
  breadth: '',
  height: '',
  available: true,
};

const emptyCategory = { name: '', description: '' };

export default function WebsiteCatalog() {
  const toast = useToast();
  const [tab, setTab] = useState('products');
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const [productModal, setProductModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [prodForm, setProdForm] = useState(emptyProduct);
  const [photoFiles, setPhotoFiles] = useState([]);
  const [savingProd, setSavingProd] = useState(false);

  const [catModal, setCatModal] = useState(false);
  const [editingCat, setEditingCat] = useState(null);
  const [catForm, setCatForm] = useState(emptyCategory);
  const [catImage, setCatImage] = useState(null);
  const [savingCat, setSavingCat] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      getWebsiteProducts(search ? { search } : {}),
      getWebsiteCategories(),
    ])
      .then(([pRes, cRes]) => {
        setProducts(pRes.data.results || pRes.data || []);
        setCategories(cRes.data.results || cRes.data || []);
      })
      .catch((err) => {
        console.error(err);
        toast.showError(err.response?.data?.detail || 'Failed to load website catalog.');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const openNewProduct = () => {
    setEditingProduct(null);
    setProdForm({ ...emptyProduct, category_id: categories[0] ? String(categories[0].id) : '' });
    setPhotoFiles([]);
    setProductModal(true);
  };

  const openEditProduct = (p) => {
    setEditingProduct(p);
    setProdForm({
      name: p.name || '',
      sku: p.sku || '',
      category_id: p.category?.id ? String(p.category.id) : '',
      quantity: p.quantity || '1 unit',
      stock: String(p.stock ?? '0'),
      price: String(p.price ?? ''),
      discount_type: p.discount_type || 'percent',
      discount: String(p.discount ?? '0'),
      description: p.description || '',
      weight: p.weight != null ? String(p.weight) : '',
      length: p.length != null ? String(p.length) : '',
      breadth: p.breadth != null ? String(p.breadth) : '',
      height: p.height != null ? String(p.height) : '',
      available: p.available !== false,
    });
    setPhotoFiles([]);
    setProductModal(true);
  };

  const saveProduct = async (e) => {
    e.preventDefault();
    if (!prodForm.name.trim() || !prodForm.sku.trim() || !prodForm.category_id) {
      toast.showWarning('Name, SKU, and category are required.');
      return;
    }
    setSavingProd(true);
    const payload = {
      name: prodForm.name.trim(),
      sku: prodForm.sku.trim(),
      category_id: Number(prodForm.category_id),
      quantity: prodForm.quantity || '1 unit',
      stock: Number(prodForm.stock) || 0,
      price: Number(prodForm.price) || 0,
      discount_type: prodForm.discount_type,
      discount: Number(prodForm.discount) || 0,
      description: prodForm.description || '',
      available: Boolean(prodForm.available),
    };
    if (prodForm.weight !== '') payload.weight = Number(prodForm.weight);
    if (prodForm.length !== '') payload.length = Number(prodForm.length);
    if (prodForm.breadth !== '') payload.breadth = Number(prodForm.breadth);
    if (prodForm.height !== '') payload.height = Number(prodForm.height);

    try {
      let productId = editingProduct?.id;
      if (editingProduct) {
        const res = await updateWebsiteProduct(editingProduct.id, payload);
        productId = res.data.id;
        toast.showSuccess('Website product updated.');
      } else {
        const res = await createWebsiteProduct(payload);
        productId = res.data.id;
        toast.showSuccess('Website product created.');
      }
      for (const file of photoFiles) {
        await uploadWebsiteProductImage(productId, file);
      }
      setProductModal(false);
      load();
    } catch (err) {
      const d = err.response?.data;
      const msg =
        d?.sku?.[0] ||
        d?.name?.[0] ||
        d?.category_id?.[0] ||
        d?.detail ||
        d?.error ||
        'Failed to save product.';
      toast.showError(typeof msg === 'string' ? msg : 'Failed to save product.');
    } finally {
      setSavingProd(false);
    }
  };

  const openNewCategory = () => {
    setEditingCat(null);
    setCatForm(emptyCategory);
    setCatImage(null);
    setCatModal(true);
  };

  const openEditCategory = (c) => {
    setEditingCat(c);
    setCatForm({ name: c.name || '', description: c.description || '' });
    setCatImage(null);
    setCatModal(true);
  };

  const saveCategory = async (e) => {
    e.preventDefault();
    if (!catForm.name.trim()) {
      toast.showWarning('Category name is required.');
      return;
    }
    setSavingCat(true);
    const fd = new FormData();
    fd.append('name', catForm.name.trim());
    fd.append('description', catForm.description || '');
    if (catImage) fd.append('image', catImage);

    try {
      if (editingCat) {
        await updateWebsiteCategory(editingCat.id, fd);
        toast.showSuccess('Category updated.');
      } else {
        await createWebsiteCategory(fd);
        toast.showSuccess('Category created.');
      }
      setCatModal(false);
      load();
    } catch (err) {
      toast.showError(err.response?.data?.name?.[0] || err.response?.data?.detail || 'Failed to save category.');
    } finally {
      setSavingCat(false);
    }
  };

  const removeProductImage = (imageId) => {
    if (!window.confirm('Remove this photo?')) return;
    deleteWebsiteProductImage(imageId)
      .then(() => {
        toast.showSuccess('Photo removed.');
        if (editingProduct) {
          getWebsiteProducts().then((r) => {
            const list = r.data.results || r.data || [];
            setProducts(list);
            const refreshed = list.find((p) => p.id === editingProduct.id);
            if (refreshed) setEditingProduct(refreshed);
          });
        } else {
          load();
        }
      })
      .catch(() => toast.showError('Could not remove photo.'));
  };

  const confirmDelete = () => {
    if (!deleteTarget) return;
    setDeleting(true);
    const req =
      deleteTarget.type === 'category'
        ? deleteWebsiteCategory(deleteTarget.id)
        : deleteWebsiteProduct(deleteTarget.id);
    req
      .then(() => {
        toast.showSuccess(deleteTarget.type === 'category' ? 'Category deleted.' : 'Product deleted.');
        setDeleteTarget(null);
        setProductModal(false);
        setCatModal(false);
        load();
      })
      .catch((err) => toast.showError(err.response?.data?.detail || 'Could not delete.'))
      .finally(() => setDeleting(false));
  };

  const filteredProducts = products.filter((p) => {
    const t = search.toLowerCase();
    if (!t) return true;
    return (
      p.name?.toLowerCase().includes(t) ||
      p.sku?.toLowerCase().includes(t) ||
      p.category?.name?.toLowerCase().includes(t)
    );
  });

  if (loading && products.length === 0 && categories.length === 0) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#64748B' }}>Loading website catalog…</div>;
  }

  return (
    <div>
      <div
        style={{
          marginBottom: 20,
          padding: '18px 20px',
          borderRadius: 14,
          background: 'linear-gradient(135deg, #EFF6FF 0%, #F8FAFC 100%)',
          border: '1px solid #BFDBFE',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 16,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <div style={{ fontSize: '0.7rem', fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#1D4ED8', marginBottom: 6 }}>
            Kushnath website
          </div>
          <h1 style={{ margin: 0, fontSize: '1.55rem', fontWeight: 900, color: '#0F172A' }}>Website Products & Categories</h1>
          <p style={{ margin: '6px 0 0', fontSize: '0.85rem', color: '#475569', maxWidth: 520 }}>
            Manage storefront catalog — products, categories, and photos. Separate from Billvice finished goods used in POS.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" className="btn-smart btn-outline-smart" onClick={openNewCategory}>
            <Plus size={16} /> Add category
          </button>
          <button type="button" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#2563EB' }} onClick={openNewProduct}>
            <Plus size={16} /> Add website product
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {[
          { key: 'products', label: `Products (${products.length})`, icon: Package },
          { key: 'categories', label: `Categories (${categories.length})`, icon: Globe },
        ].map((t) => {
          const Icon = t.icon;
          const on = tab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`btn-smart ${on ? 'btn-primary-smart' : 'btn-outline-smart'}`}
              style={{ backgroundColor: on ? '#2563EB' : undefined, fontWeight: 700 }}
            >
              <Icon size={16} /> {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'products' && (
        <div className="smart-card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 16px', borderBottom: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ position: 'relative', width: 300, maxWidth: '100%' }}>
              <Search size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
              <input
                className="form-control-smart"
                style={{ paddingLeft: 34, height: 36 }}
                placeholder="Search name, SKU, category…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && load()}
              />
            </div>
            <button type="button" className="btn-smart btn-outline-smart" onClick={load}>Refresh</button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="smart-table">
              <thead>
                <tr>
                  <th>Photo</th>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>Category</th>
                  <th>Price</th>
                  <th>Stock</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((p) => {
                  const thumb = p.images?.[0]?.image;
                  return (
                    <tr key={p.id}>
                      <td>
                        {thumb ? (
                          <img src={mediaUrl(thumb)} alt="" style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 8, border: '1px solid #E2E8F0' }} />
                        ) : (
                          <div style={{ width: 48, height: 48, borderRadius: 8, background: '#F1F5F9', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                            <ImagePlus size={18} />
                          </div>
                        )}
                      </td>
                      <td style={{ fontWeight: 700 }}>{p.name}</td>
                      <td style={{ color: '#64748B' }}>{p.sku}</td>
                      <td>{p.category?.name || '—'}</td>
                      <td style={{ fontWeight: 800 }}>₹{Number(p.price).toFixed(2)}</td>
                      <td>{p.stock}</td>
                      <td>
                        <span className="badge-smart" style={{ background: p.available ? '#ECFDF5' : '#FEE2E2', color: p.available ? '#047857' : '#B91C1C' }}>
                          {p.available ? 'Live' : 'Hidden'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'inline-flex', gap: 6 }}>
                          <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 10px', fontSize: '0.75rem' }} onClick={() => openEditProduct(p)}>
                            <Pencil size={14} /> Edit
                          </button>
                          <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 8px', fontSize: '0.75rem', color: '#DC2626', borderColor: '#FCA5A5' }} onClick={() => setDeleteTarget({ type: 'product', id: p.id, name: p.name })}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredProducts.length === 0 && (
                  <tr>
                    <td colSpan="8" style={{ textAlign: 'center', padding: 32, color: '#94A3B8' }}>No website products found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'categories' && (
        <div className="smart-card" style={{ overflow: 'hidden' }}>
          <table className="smart-table">
            <thead>
              <tr>
                <th>Image</th>
                <th>Name</th>
                <th>Description</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((c) => (
                <tr key={c.id}>
                  <td>
                    {c.image ? (
                      <img src={mediaUrl(c.image)} alt="" style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 8, border: '1px solid #E2E8F0' }} />
                    ) : (
                      <div style={{ width: 48, height: 48, borderRadius: 8, background: '#F1F5F9', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                        <ImagePlus size={18} />
                      </div>
                    )}
                  </td>
                  <td style={{ fontWeight: 700 }}>{c.name}</td>
                  <td style={{ color: '#64748B', maxWidth: 360 }}>{c.description || '—'}</td>
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ display: 'inline-flex', gap: 6 }}>
                      <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 10px', fontSize: '0.75rem' }} onClick={() => openEditCategory(c)}>
                        <Pencil size={14} /> Edit
                      </button>
                      <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 8px', fontSize: '0.75rem', color: '#DC2626', borderColor: '#FCA5A5' }} onClick={() => setDeleteTarget({ type: 'category', id: c.id, name: c.name })}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {categories.length === 0 && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', padding: 32, color: '#94A3B8' }}>No categories yet. Add one to start listing products.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Product modal */}
      {productModal && (
        <div className="modal-backdrop" onClick={() => !savingProd && setProductModal(false)}>
          <div className="modal-content-smart" style={{ maxWidth: 640, maxHeight: '92vh', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontWeight: 800 }}>{editingProduct ? 'Edit website product' : 'Add website product'}</h3>
              <button type="button" onClick={() => setProductModal(false)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#94A3B8' }}><X size={20} /></button>
            </div>
            <form onSubmit={saveProduct}>
              <div className="form-field">
                <label className="form-field-label">Product name *</label>
                <input className="form-control-smart" required value={prodForm.name} onChange={(e) => setProdForm({ ...prodForm, name: e.target.value })} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-field">
                  <label className="form-field-label">SKU *</label>
                  <input className="form-control-smart" required value={prodForm.sku} onChange={(e) => setProdForm({ ...prodForm, sku: e.target.value })} />
                </div>
                <div className="form-field">
                  <label className="form-field-label">Category *</label>
                  <select className="form-control-smart" required value={prodForm.category_id} onChange={(e) => setProdForm({ ...prodForm, category_id: e.target.value })}>
                    <option value="">Select category…</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-field">
                  <label className="form-field-label">Pack / quantity label</label>
                  <input className="form-control-smart" value={prodForm.quantity} onChange={(e) => setProdForm({ ...prodForm, quantity: e.target.value })} placeholder="e.g. 100g, 1 bottle" />
                </div>
                <div className="form-field">
                  <label className="form-field-label">Website stock *</label>
                  <input type="number" min="0" className="form-control-smart" required value={prodForm.stock} onChange={(e) => setProdForm({ ...prodForm, stock: e.target.value })} />
                </div>
                <div className="form-field">
                  <label className="form-field-label">Price (₹) *</label>
                  <input type="number" min="0" step="0.01" className="form-control-smart" required value={prodForm.price} onChange={(e) => setProdForm({ ...prodForm, price: e.target.value })} />
                </div>
                <div className="form-field">
                  <label className="form-field-label">Discount type</label>
                  <select className="form-control-smart" value={prodForm.discount_type} onChange={(e) => setProdForm({ ...prodForm, discount_type: e.target.value })}>
                    <option value="percent">Percent %</option>
                    <option value="amount">Amount ₹</option>
                  </select>
                </div>
                <div className="form-field">
                  <label className="form-field-label">Discount</label>
                  <input type="number" min="0" step="0.01" className="form-control-smart" value={prodForm.discount} onChange={(e) => setProdForm({ ...prodForm, discount: e.target.value })} />
                </div>
                <div className="form-field" style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 22 }}>
                  <input type="checkbox" id="web-avail" checked={prodForm.available} onChange={(e) => setProdForm({ ...prodForm, available: e.target.checked })} />
                  <label htmlFor="web-avail" className="form-field-label" style={{ marginBottom: 0 }}>Available on website</label>
                </div>
              </div>
              <div className="form-field">
                <label className="form-field-label">Description</label>
                <textarea className="form-control-smart" rows={3} value={prodForm.description} onChange={(e) => setProdForm({ ...prodForm, description: e.target.value })} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12 }}>
                {[
                  ['weight', 'Weight'],
                  ['length', 'Length'],
                  ['breadth', 'Breadth'],
                  ['height', 'Height'],
                ].map(([k, label]) => (
                  <div key={k} className="form-field">
                    <label className="form-field-label">{label}</label>
                    <input type="number" step="0.01" min="0" className="form-control-smart" value={prodForm[k]} onChange={(e) => setProdForm({ ...prodForm, [k]: e.target.value })} />
                  </div>
                ))}
              </div>

              {editingProduct?.images?.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <label className="form-field-label">Current photos</label>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {editingProduct.images.map((img) => (
                      <div key={img.id} style={{ position: 'relative' }}>
                        <img src={mediaUrl(img.image)} alt="" style={{ width: 72, height: 72, objectFit: 'cover', borderRadius: 8, border: '1px solid #E2E8F0' }} />
                        <button type="button" onClick={() => removeProductImage(img.id)} style={{ position: 'absolute', top: -6, right: -6, border: 'none', background: '#DC2626', color: '#fff', borderRadius: '50%', width: 20, height: 20, cursor: 'pointer', fontSize: 12 }}>×</button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="form-field">
                <label className="form-field-label">Upload photos</label>
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  className="form-control-smart"
                  onChange={(e) => setPhotoFiles(Array.from(e.target.files || []))}
                />
                {photoFiles.length > 0 && (
                  <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>{photoFiles.length} file(s) selected</div>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
                <button type="button" className="btn-smart btn-secondary-smart" disabled={savingProd} onClick={() => setProductModal(false)}>Cancel</button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#2563EB' }} disabled={savingProd}>
                  {savingProd ? 'Saving…' : editingProduct ? 'Update product' : 'Save product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Category modal */}
      {catModal && (
        <div className="modal-backdrop" onClick={() => !savingCat && setCatModal(false)}>
          <div className="modal-content-smart" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontWeight: 800 }}>{editingCat ? 'Edit category' : 'Add category'}</h3>
              <button type="button" onClick={() => setCatModal(false)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#94A3B8' }}><X size={20} /></button>
            </div>
            <form onSubmit={saveCategory}>
              <div className="form-field">
                <label className="form-field-label">Category name *</label>
                <input className="form-control-smart" required value={catForm.name} onChange={(e) => setCatForm({ ...catForm, name: e.target.value })} />
              </div>
              <div className="form-field">
                <label className="form-field-label">Description</label>
                <textarea className="form-control-smart" rows={3} value={catForm.description} onChange={(e) => setCatForm({ ...catForm, description: e.target.value })} />
              </div>
              {editingCat?.image && (
                <div style={{ marginBottom: 12 }}>
                  <label className="form-field-label">Current image</label>
                  <img src={mediaUrl(editingCat.image)} alt="" style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 8, border: '1px solid #E2E8F0' }} />
                </div>
              )}
              <div className="form-field">
                <label className="form-field-label">Category photo</label>
                <input type="file" accept="image/*" className="form-control-smart" onChange={(e) => setCatImage(e.target.files?.[0] || null)} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                <button type="button" className="btn-smart btn-secondary-smart" disabled={savingCat} onClick={() => setCatModal(false)}>Cancel</button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#2563EB' }} disabled={savingCat}>
                  {savingCat ? 'Saving…' : editingCat ? 'Update category' : 'Save category'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmationModal
        isOpen={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title={deleteTarget?.type === 'category' ? 'Delete category?' : 'Delete product?'}
        message={`Delete “${deleteTarget?.name || ''}”? This affects the Kushnath website catalog.`}
        confirmText="Delete"
        isDanger
        loading={deleting}
      />
    </div>
  );
}
