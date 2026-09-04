import React from 'react';
import { AlertTriangle } from 'lucide-react';

export default function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDanger = false,
  loading = false,
}) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content-smart" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '440px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', marginBottom: '16px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              backgroundColor: isDanger ? '#FEE2E2' : '#FEF3C7',
              color: isDanger ? '#DC2626' : '#D97706',
              display: 'flex',
              alignItems: 'center',
              justify: 'center',
              flexShrink: 0,
            }}
          >
            <AlertTriangle size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#0F172A', marginBottom: '6px' }}>{title}</h3>
            <div style={{ fontSize: '0.875rem', color: '#64748B', lineHeight: '1.4' }}>{message}</div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
          <button onClick={onClose} disabled={loading} className="btn-smart btn-outline-smart">
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="btn-smart"
            style={{
              backgroundColor: isDanger ? '#DC2626' : '#059669',
              color: '#FFFFFF',
            }}
          >
            {loading ? 'Processing...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
