function isNumberBox(el) {
  if (!(el instanceof HTMLInputElement)) return false;
  if (el.readOnly || el.disabled) return false;
  const type = (el.type || 'text').toLowerCase();
  if (type === 'number') return true;
  const mode = (el.inputMode || '').toLowerCase();
  if (mode === 'decimal' || mode === 'numeric') return true;
  return false;
}

function isZeroValue(value) {
  const s = String(value ?? '').trim();
  if (!s || s === '-') return false;
  if (!/^-?0+(\.0+)?$/.test(s)) return false;
  return Number(s) === 0;
}

function setNativeValue(el, next) {
  const proto = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
  proto?.set?.call(el, next);
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

export function attachClearZeroOnType() {
  const onFocusIn = (e) => {
    const el = e.target;
    if (!isNumberBox(el) || !isZeroValue(el.value)) return;
    requestAnimationFrame(() => {
      try {
        el.select();
      } catch {
        /* ignore */
      }
    });
  };

  const onKeyDown = (e) => {
    const el = e.target;
    if (!isNumberBox(el) || !isZeroValue(el.value)) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === '.' || e.key === ',') return;
    if (!/^[0-9]$/.test(e.key)) return;
    e.preventDefault();
    setNativeValue(el, e.key);
  };

  document.addEventListener('focusin', onFocusIn);
  document.addEventListener('keydown', onKeyDown, true);
  return () => {
    document.removeEventListener('focusin', onFocusIn);
    document.removeEventListener('keydown', onKeyDown, true);
  };
}
