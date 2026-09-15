import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getSuppliers, createSupplier, updateSupplier, deleteSupplier } from '../api';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { useToast } from '../components/ToastContext';
import ConfirmationModal from '../components/ConfirmationModal';

const emptyForm = { name: '', gstin: '', phone: '', email: '', address: '', state: '', contact_person: '', gst_type: 'registered' };

export default function Suppliers() {
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const toast = useToast();

  const load = () => getSuppliers().then((r) => setRows(r.data.results || r.data));
  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setOpen(true);
  };

  const openEdit = (s) => {
    setEditing(s);
    setForm({
      name: s.name || '',
      gstin: s.gstin || '',
      phone: s.phone || '',
      email: s.email || '',
      address: s.address || '',
      state: s.state || '',
      contact_person: s.contact_person || '',
      gst_type: s.gst_type || 'registered',
    });
    setOpen(true);
  };

  const save = (e) => {
    e.preventDefault();
    const req = editing ? updateSupplier(editing.id, form) : createSupplier(form);
    req.then(() => {
      toast.showSuccess(editing ? 'Supplier updated.' : 'Supplier saved.');
      setOpen(false);
      setEditing(null);
      setForm(emptyForm);
      load();
    }).catch((err) => toast.showError(err.response?.data?.gstin?.[0] || err.response?.data?.name?.[0] || 'Could not save supplier.'));
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <Link to="/purchase-orders" style={{ fontSize: 13, color: '#059669' }}>← Purchase</Link>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Suppliers</h1>
        </div>
        <button className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }} onClick={openCreate}><Plus size={16} /> Add supplier</button>
      </div>
      <div className="smart-card">
        <table className="smart-table">
          <thead>
            <tr><th>Name</th><th>GSTIN</th><th>Type</th><th>Phone</th><th>State</th><th>Address</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td style={{ fontWeight: 700 }}>{s.name}</td>
                <td>{s.gstin || '—'}</td>
                <td>{s.gst_type}</td>
                <td>{s.phone || '—'}</td>
                <td>{s.state || s.state_code || '—'}</td>
                <td>{s.address || '—'}</td>
                <td>
                  <span style={{ display: 'inline-flex', gap: 6 }}>
                    <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 8px' }} onClick={() => openEdit(s)}><Pencil size={14} /></button>
                    <button type="button" className="btn-smart btn-outline-smart" style={{ padding: '4px 8px', color: '#DC2626' }} onClick={() => setDeleteTarget(s)}><Trash2 size={14} /></button>
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan="7" style={{ textAlign: 'center', padding: 28, color: '#94A3B8' }}>No suppliers yet.</td></tr>}
          </tbody>
        </table>
      </div>
      {open && (
        <div className="modal-backdrop" onClick={() => setOpen(false)}>
          <div className="modal-content-smart" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontWeight: 800, marginBottom: 12 }}>{editing ? 'Edit supplier' : 'Add supplier'}</h3>
            <form onSubmit={save}>
              {['name', 'gstin', 'phone', 'email', 'state', 'address', 'contact_person'].map((k) => (
                <input key={k} className="form-control-smart" style={{ marginBottom: 8 }} placeholder={k.replace('_', ' ')} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} required={k === 'name'} />
              ))}
              <select className="form-control-smart" style={{ marginBottom: 12 }} value={form.gst_type} onChange={(e) => setForm({ ...form, gst_type: e.target.value })}>
                <option value="registered">Registered</option>
                <option value="unregistered">Unregistered</option>
                <option value="composition">Composition</option>
              </select>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                <button type="button" className="btn-smart btn-outline-smart" onClick={() => setOpen(false)}>Cancel</button>
                <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }}>Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
      <ConfirmationModal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete supplier"
        message={`Delete “${deleteTarget?.name || ''}”?`}
        confirmText="Delete"
        isDanger
        loading={deleting}
        onConfirm={() => {
          setDeleting(true);
          deleteSupplier(deleteTarget.id)
            .then(() => {
              toast.showSuccess('Supplier deleted.');
              setDeleteTarget(null);
              load();
            })
            .catch((err) => toast.showError(err.response?.data?.detail || err.response?.data?.error || 'Could not delete supplier.'))
            .finally(() => setDeleting(false));
        }}
      />
    </div>
  );
}
