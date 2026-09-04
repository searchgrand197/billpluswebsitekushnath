import React from 'react';
import { allowedGstRates, beforeFromInclusive, money, normalizeGstRate, sellingGstMath } from '../pages/poUtils';

export default function PricingGstCard({
  settings,
  costPrice,
  sellingBefore,
  sellingAfter,
  gstRate,
  priceMode = 'before',
  onChange,
  compact = false,
}) {
  const rates = allowedGstRates(settings);
  const gst = normalizeGstRate(gstRate, settings?.gst_percentage ?? 0);
  const math = priceMode === 'after'
    ? beforeFromInclusive(sellingAfter, gst)
    : sellingGstMath(sellingBefore, gst);

  const set = (patch) => onChange({ costPrice, sellingBefore, sellingAfter, gstRate: gst, priceMode, ...patch });

  return (
    <div style={{ border: '1px solid #E2E8F0', borderRadius: 12, padding: compact ? 12 : 16, background: '#F8FAFC' }}>
      <div style={{ fontWeight: 800, fontSize: '0.85rem', color: '#0F172A', marginBottom: 12 }}>Pricing & GST</div>
      <div style={{ marginBottom: 10 }}>
        <label className="pos-field-label">Price entry mode</label>
        <select
          className="form-control-smart"
          value={priceMode}
          onChange={(e) => set({ priceMode: e.target.value })}
        >
          <option value="before">Before GST</option>
          <option value="after">After GST (inclusive)</option>
        </select>
        <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>Choose whether you want to enter the price before GST or the final GST-inclusive price.</div>
      </div>
      <div style={{ marginBottom: 10 }}>
        <label className="pos-field-label">Purchase price before GST</label>
        <input
          type="number"
          min="0"
          step="0.01"
          className="form-control-smart"
          value={costPrice}
          onChange={(e) => set({ costPrice: e.target.value })}
        />
      </div>
      {priceMode === 'before' ? (
        <div style={{ marginBottom: 10 }}>
          <label className="pos-field-label">Selling price before GST</label>
          <input
            type="number"
            min="0"
            step="0.01"
            className="form-control-smart"
            required
            value={sellingBefore}
            onChange={(e) => set({ sellingBefore: e.target.value })}
            style={{ fontSize: '1.05rem', fontWeight: 700 }}
          />
          <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>Base selling price before GST.</div>
        </div>
      ) : (
        <div style={{ marginBottom: 10 }}>
          <label className="pos-field-label">Selling price after GST</label>
          <input
            type="number"
            min="0"
            step="0.01"
            className="form-control-smart"
            required
            value={sellingAfter}
            onChange={(e) => set({ sellingAfter: e.target.value })}
            style={{ fontSize: '1.05rem', fontWeight: 700 }}
          />
          <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>Final selling price including GST.</div>
        </div>
      )}
      <div style={{ marginBottom: 10 }}>
        <label className="pos-field-label">GST rate</label>
        <select className="form-control-smart" value={gst} onChange={(e) => set({ gstRate: e.target.value })}>
          {rates.map((g) => (
            <option key={g} value={String(g)}>{g}%</option>
          ))}
        </select>
        <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 4 }}>GST applicable to this product. Default comes from Settings.</div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#475569', marginBottom: 8 }}>
        <span>GST amount</span>
        <strong>{money(math.gstAmount)}</strong>
      </div>
      <div style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: 10, padding: '10px 12px' }}>
        <div style={{ fontSize: 11, fontWeight: 800, color: '#047857', letterSpacing: '0.04em' }}>SELLING PRICE AFTER GST</div>
        <div style={{ fontSize: '1.35rem', fontWeight: 900, color: '#059669' }}>{money(math.after)}</div>
        <div style={{ fontSize: 11, color: '#047857' }}>Final selling price including GST. Billing uses the before-GST rate so GST is not applied twice.</div>
      </div>
      {priceMode === 'after' && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#64748B' }}>Selling price before GST: <strong>{money(math.before)}</strong></div>
      )}
    </div>
  );
}
