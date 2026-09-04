/** Mass / volume unit helpers for Ayurvedic & medicine inventory. */

export const MASS_UNITS = ['mg', 'g', 'kg'];
export const VOLUME_UNITS = ['ml', 'l'];

const MASS_TO_MG = { mg: 1, g: 1000, kg: 1000000 };
const VOL_TO_ML = { ml: 1, l: 1000 };

export function getInputUnitOptions(stockUnit) {
  const u = (stockUnit || 'unit').toLowerCase();
  if (MASS_UNITS.includes(u)) {
    return [
      { value: 'mg', label: 'mg (milligram)' },
      { value: 'g', label: 'g (gram)' },
      { value: 'kg', label: 'kg' },
    ];
  }
  if (VOLUME_UNITS.includes(u)) {
    return [
      { value: 'ml', label: 'ml' },
      { value: 'l', label: 'L (litre)' },
    ];
  }
  return [{ value: u || 'unit', label: u === 'unit' ? 'pcs' : u }];
}

export function convertQty(qty, fromUnit, toUnit) {
  const from = (fromUnit || '').toLowerCase();
  const to = (toUnit || '').toLowerCase();
  const n = Number(qty) || 0;
  if (!from || !to || from === to) return n;
  if (MASS_TO_MG[from] && MASS_TO_MG[to]) {
    return (n * MASS_TO_MG[from]) / MASS_TO_MG[to];
  }
  if (VOL_TO_ML[from] && VOL_TO_ML[to]) {
    return (n * VOL_TO_ML[from]) / VOL_TO_ML[to];
  }
  return n;
}

/** Human-friendly qty for medicine (shows mg when stock is in g/kg). */
export function formatQtyDisplay(qty, unit) {
  const n = Number(qty) || 0;
  const u = (unit || '').toLowerCase();
  if (u === 'mg') return `${n.toFixed(2)} mg`;
  if (u === 'g') {
    if (n > 0 && n < 1) return `${n.toFixed(4)} g (${(n * 1000).toFixed(2)} mg)`;
    return `${n.toFixed(3)} g`;
  }
  if (u === 'kg') {
    if (n > 0 && n < 0.001) return `${n.toFixed(6)} kg (${(n * 1000000).toFixed(2)} mg)`;
    if (n > 0 && n < 1) return `${n.toFixed(4)} kg (${(n * 1000).toFixed(2)} g)`;
    return `${n.toFixed(3)} kg`;
  }
  if (u === 'ml') return `${n.toFixed(2)} ml`;
  if (u === 'l') {
    if (n > 0 && n < 1) return `${n.toFixed(4)} l (${(n * 1000).toFixed(2)} ml)`;
    return `${n.toFixed(3)} l`;
  }
  return `${n.toFixed(3)} ${u || 'unit'}`;
}

export function formatQty(n) {
  if (!Number.isFinite(n)) return '0';
  return Number(n.toFixed(6)).toString();
}

export const RAW_MATERIAL_UNIT_OPTIONS = [
  { value: 'mg', label: 'mg (Milligram)' },
  { value: 'g', label: 'g (Gram)' },
  { value: 'kg', label: 'kg (Kilogram)' },
  { value: 'ml', label: 'ml (Milliliter)' },
  { value: 'l', label: 'l (Liter)' },
  { value: 'unit', label: 'Units / Pieces' },
];

export const PRODUCT_UOM_OPTIONS = [
  { value: 'unit', label: 'Piece / Unit (tablet, capsule, bottle)' },
  { value: 'mg', label: 'mg (Milligram)' },
  { value: 'g', label: 'g (Gram)' },
  { value: 'kg', label: 'kg (Kilogram)' },
];
