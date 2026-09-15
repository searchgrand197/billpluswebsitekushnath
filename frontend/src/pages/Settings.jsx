import React, { useEffect, useState } from 'react';
import { getCompanySettings, createCompanySettings, updateCompanySettings } from '../api';
import { Settings as SettingsIcon, Save, Building, Printer, CheckCircle, Percent, Leaf, Shield } from 'lucide-react';
import { useToast } from '../components/ToastContext';

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('business');
  const toast = useToast();

  useEffect(() => {
    getCompanySettings()
      .then((res) => {
        const dataList = res.data.results || res.data;
        if (dataList && dataList.length > 0) {
          setSettings(dataList[0]);
        } else {
          setSettings({});
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        toast.showError('Failed to load company settings.');
        setSettings({});
        setLoading(false);
      });
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!settings.id) {
      createCompanySettings(settings)
        .then((res) => {
          setSettings(res.data);
          toast.showSuccess('Company & ERP Settings saved successfully!');
        })
        .catch((err) => {
          console.error(err);
          toast.showError('Failed to create company settings.');
        });
    } else {
      updateCompanySettings(settings.id, settings)
        .then(() => {
          toast.showSuccess('Company & ERP Settings saved successfully!');
        })
        .catch((err) => {
          console.error(err);
          toast.showError('Failed to update company settings.');
        });
    }
  };

  const handleChange = (field, value) => {
    setSettings({ ...settings, [field]: value });
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Loading Business Settings...</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A' }}>Ayurvedic ERP Settings</h1>
        <p style={{ fontSize: '0.85rem', color: '#64748B' }}>Configure business details, GSTIN tax, default thresholds, and thermal invoice printing.</p>
      </div>

      {/* Category Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #E2E8F0', marginBottom: '24px' }}>
        <button
          onClick={() => setActiveCategory('business')}
          className={`btn-smart ${activeCategory === 'business' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
          style={{ backgroundColor: activeCategory === 'business' ? '#059669' : undefined, borderRadius: '8px 8px 0 0' }}
        >
          <Building size={16} /> Business Profile
        </button>
        <button
          onClick={() => setActiveCategory('invoice')}
          className={`btn-smart ${activeCategory === 'invoice' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
          style={{ backgroundColor: activeCategory === 'invoice' ? '#059669' : undefined, borderRadius: '8px 8px 0 0' }}
        >
          <Percent size={16} /> Invoice & Tax Settings
        </button>
        <button
          onClick={() => setActiveCategory('printer')}
          className={`btn-smart ${activeCategory === 'printer' ? 'btn-primary-smart' : 'btn-outline-smart'}`}
          style={{ backgroundColor: activeCategory === 'printer' ? '#059669' : undefined, borderRadius: '8px 8px 0 0' }}
        >
          <Printer size={16} /> Printer & Thermal POS Layout
        </button>
      </div>

      <form onSubmit={handleSubmit} style={{ maxWidth: '800px' }}>
        {/* Category 1: Business Profile */}
        {activeCategory === 'business' && (
          <div className="smart-card" style={{ padding: '24px', marginBottom: '24px' }}>
            <h3 style={{ fontWeight: '700', fontSize: '1rem', color: '#0F172A', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Building size={18} color="#059669" /> Company Profile & Address
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label className="pos-field-label">COMPANY NAME *</label>
                <input
                  type="text"
                  required
                  className="form-control-smart"
                  value={settings?.company_name || ''}
                  onChange={(e) => handleChange('company_name', e.target.value)}
                />
              </div>
              <div>
                <label className="pos-field-label">GSTIN NUMBER</label>
                <input
                  type="text"
                  placeholder="e.g. 07AAAAA0000A1Z5"
                  className="form-control-smart"
                  value={settings?.gstin || ''}
                  onChange={(e) => handleChange('gstin', e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label className="pos-field-label">PHONE NUMBER</label>
                <input
                  type="text"
                  className="form-control-smart"
                  value={settings?.phone || ''}
                  onChange={(e) => handleChange('phone', e.target.value)}
                />
              </div>
              <div>
                <label className="pos-field-label">EMAIL ADDRESS</label>
                <input
                  type="email"
                  className="form-control-smart"
                  value={settings?.email || ''}
                  onChange={(e) => handleChange('email', e.target.value)}
                />
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label className="pos-field-label">ADDRESS LINE 1</label>
              <input
                type="text"
                className="form-control-smart"
                value={settings?.address_line1 || ''}
                onChange={(e) => handleChange('address_line1', e.target.value)}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
              <div>
                <label className="pos-field-label">CITY</label>
                <input
                  type="text"
                  className="form-control-smart"
                  value={settings?.city || ''}
                  onChange={(e) => handleChange('city', e.target.value)}
                />
              </div>
              <div>
                <label className="pos-field-label">STATE</label>
                <input
                  type="text"
                  className="form-control-smart"
                  value={settings?.state || ''}
                  onChange={(e) => handleChange('state', e.target.value)}
                />
              </div>
              <div>
                <label className="pos-field-label">POSTAL CODE</label>
                <input
                  type="text"
                  className="form-control-smart"
                  value={settings?.postal_code || ''}
                  onChange={(e) => handleChange('postal_code', e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {/* Category 2: Invoice Settings */}
        {activeCategory === 'invoice' && (
          <div className="smart-card" style={{ padding: '24px', marginBottom: '24px' }}>
            <h3 style={{ fontWeight: '700', fontSize: '1rem', color: '#0F172A', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Percent size={18} color="#059669" /> Invoice Defaults & GST Tax
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label className="pos-field-label">DEFAULT GST TAX RATE (%)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="form-control-smart"
                  value={settings?.gst_percentage ?? 5}
                  onChange={(e) => handleChange('gst_percentage', e.target.value)}
                />
                <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>
                  Used as the default GST % on new products, raw materials, purchase orders, and sales invoices. Typical rates: 0, 5, 12, 18, 28.
                </div>
              </div>
              <div>
                <label className="pos-field-label">DEFAULT CREDIT DUE DAYS</label>
                <input
                  type="number"
                  className="form-control-smart"
                  value={settings?.dues_days ?? 7}
                  onChange={(e) => handleChange('dues_days', e.target.value)}
                />
                <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>
                  Number of days after a sales invoice before payment is due. This is not a GST rate.
                </div>
              </div>
            </div>

            <div>
              <label className="pos-field-label">INVOICE FOOTER / TERMS & CONDITIONS</label>
              <textarea
                rows="3"
                className="form-control-smart"
                value={settings?.invoice_footer_text || ''}
                onChange={(e) => handleChange('invoice_footer_text', e.target.value)}
                placeholder="e.g. Thank you for buying Ayurvedic Healthcare products! Goods once sold will not be taken back."
              />
            </div>
          </div>
        )}

        {/* Category 3: Printer Format */}
        {activeCategory === 'printer' && (
          <div className="smart-card" style={{ padding: '24px', marginBottom: '24px' }}>
            <h3 style={{ fontWeight: '700', fontSize: '1rem', color: '#0F172A', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Printer size={18} color="#059669" /> Thermal Printer & Layout Configuration
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <label className="pos-field-label">PRINTER PAPER LAYOUT</label>
                <select
                  className="form-control-smart"
                  value={settings?.printer_type || 'thermal_80mm'}
                  onChange={(e) => handleChange('printer_type', e.target.value)}
                >
                  <option value="thermal_80mm">Thermal 80mm POS Receipt</option>
                  <option value="thermal_58mm">Thermal 58mm POS Receipt</option>
                  <option value="a4">Standard A4 / Letter Page</option>
                </select>
              </div>
              <div>
                <label className="pos-field-label">EXACT PRINTER NAME (OPTIONAL)</label>
                <input
                  type="text"
                  placeholder="e.g. POS-80 Series Printer"
                  className="form-control-smart"
                  value={settings?.printer_name || ''}
                  onChange={(e) => handleChange('printer_name', e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        <button type="submit" className="btn-smart btn-primary-smart" style={{ backgroundColor: '#059669' }}>
          <Save size={18} /> Save Settings
        </button>
      </form>
    </div>
  );
}
