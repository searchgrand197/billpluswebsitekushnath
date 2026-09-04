export const GST_RATES = [0, 5, 12, 18, 28];

export function allowedGstRates(settings) {
  const set = new Set(GST_RATES.map(Number));
  const configured = Number(settings?.gst_percentage);
  if (!Number.isNaN(configured) && configured >= 0) set.add(configured);
  return [...set].sort((a, b) => a - b);
}

/** Keep GST select value in sync with options ("18.00" must become "18", 0 stays "0"). */
export function normalizeGstRate(value, fallback = 0) {
  if (value === '' || value === null || value === undefined) return String(fallback);
  const n = Number(value);
  if (Number.isNaN(n)) return String(fallback);
  return String(n);
}

export function sellingGstMath(before, gstPct) {
  const base = Math.max(0, Number(before) || 0);
  const rate = Math.max(0, Number(gstPct) || 0);
  const gstAmount = Math.round((base * rate / 100) * 100) / 100;
  const after = Math.round((base + gstAmount) * 100) / 100;
  return {
    before: Math.round(base * 100) / 100,
    gstAmount: Math.round(gstAmount * 100) / 100,
    after,
  };
}

export function beforeFromInclusive(after, gstPct) {
  const inclusive = Math.max(0, Number(after) || 0);
  const rate = Math.max(0, Number(gstPct) || 0);
  const before = rate === 0 ? inclusive : inclusive / (1 + rate / 100);
  return sellingGstMath(before, rate);
}

export const PAYMENT_MODE_STYLE = {
  cash: { bg: '#D1FAE5', color: '#065F46', border: '#6EE7B7', label: 'Cash' },
  upi: { bg: '#EDE9FE', color: '#5B21B6', border: '#C4B5FD', label: 'UPI' },
  bank: { bg: '#DBEAFE', color: '#1D4ED8', border: '#93C5FD', label: 'Bank' },
  bank_transfer: { bg: '#DBEAFE', color: '#1D4ED8', border: '#93C5FD', label: 'Bank' },
  card: { bg: '#CFFAFE', color: '#0E7490', border: '#67E8F9', label: 'Card' },
  credit: { bg: '#FFEDD5', color: '#C2410C', border: '#FDBA74', label: 'Credit' },
  other: { bg: '#F1F5F9', color: '#475569', border: '#CBD5E1', label: 'Other' },
};

export function paymentModeStyle(mode) {
  const key = String(mode || '').toLowerCase().replace(/\s+/g, '_');
  return PAYMENT_MODE_STYLE[key] || PAYMENT_MODE_STYLE.other;
}

export const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat',
  'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh',
  'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan',
  'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry',
];

const GST_STATE_CODES = {
  'andhra pradesh': '37', 'arunachal pradesh': '12', 'assam': '18', 'bihar': '10',
  'chhattisgarh': '22', 'goa': '30', 'gujarat': '24', 'haryana': '06',
  'himachal pradesh': '02', 'jharkhand': '20', 'karnataka': '29', 'kerala': '32',
  'madhya pradesh': '23', 'maharashtra': '27', 'manipur': '14', 'meghalaya': '17',
  'mizoram': '15', 'nagaland': '13', 'odisha': '21', 'punjab': '03', 'rajasthan': '08',
  'sikkim': '11', 'tamil nadu': '33', 'telangana': '36', 'tripura': '16',
  'uttar pradesh': '09', 'uttarakhand': '05', 'west bengal': '19',
  'andaman and nicobar islands': '35', 'chandigarh': '04',
  'dadra and nagar haveli and daman and diu': '26', 'delhi': '07',
  'jammu and kashmir': '01', 'ladakh': '38', 'lakshadweep': '31', 'puducherry': '34',
};

function normState(name) {
  return String(name || '').trim().toLowerCase().replace(/\s+/g, ' ');
}

function gstinCode(gstin) {
  const s = String(gstin || '').trim().toUpperCase().slice(0, 2);
  return /^\d{2}$/.test(s) ? s : '';
}

export function saleIsInterstate({ companyGstin = '', companyState = '', customerGstin = '', customerState = '' } = {}) {
  const party = gstinCode(customerGstin) || GST_STATE_CODES[normState(customerState)] || '';
  const company = gstinCode(companyGstin) || GST_STATE_CODES[normState(companyState)] || '';
  if (party && company) return party !== company;
  const ps = normState(customerState);
  const cs = normState(companyState);
  if (ps && cs) return ps !== cs;
  return false;
}

export const PAYMENT_TERMS = [
  { value: 'advance', label: 'Advance' },
  { value: 'cod', label: 'Cash on Delivery' },
  { value: '7', label: '7 Days' },
  { value: '15', label: '15 Days' },
  { value: '30', label: '30 Days' },
  { value: '45', label: '45 Days' },
  { value: '60', label: '60 Days' },
  { value: 'custom', label: 'Custom' },
];

export const STATUS_STYLE = {
  draft: { bg: '#F1F5F9', color: '#475569' },
  ordered: { bg: '#DBEAFE', color: '#1D4ED8' },
  partially_received: { bg: '#FEF3C7', color: '#B45309' },
  received: { bg: '#ECFDF5', color: '#047857' },
  cancelled: { bg: '#FEE2E2', color: '#B91C1C' },
  closed: { bg: '#E2E8F0', color: '#334155' },
};

export function statusLabel(status) {
  return (status || '').replace(/_/g, ' ');
}

export function money(n) {
  return `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
const TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];

function twoDigit(n) {
  if (n < 20) return ONES[n];
  const t = Math.floor(n / 10);
  const o = n % 10;
  return `${TENS[t]}${o ? ` ${ONES[o]}` : ''}`.trim();
}

function threeDigit(n) {
  const h = Math.floor(n / 100);
  const rest = n % 100;
  const parts = [];
  if (h) parts.push(`${ONES[h]} Hundred`);
  if (rest) parts.push(twoDigit(rest));
  return parts.join(' ');
}

export function amountInWords(value) {
  const num = Math.round(Number(value || 0) * 100) / 100;
  if (!num) return 'Rupees Zero Only';
  const rupees = Math.floor(num);
  const paise = Math.round((num - rupees) * 100);
  const crore = Math.floor(rupees / 10000000);
  const lakh = Math.floor((rupees % 10000000) / 100000);
  const thousand = Math.floor((rupees % 100000) / 1000);
  const hundred = rupees % 1000;
  const parts = [];
  if (crore) parts.push(`${threeDigit(crore)} Crore`);
  if (lakh) parts.push(`${threeDigit(lakh)} Lakh`);
  if (thousand) parts.push(`${threeDigit(thousand)} Thousand`);
  if (hundred) parts.push(threeDigit(hundred));
  let out = `Rupees ${parts.join(' ')}`.replace(/\s+/g, ' ').trim();
  if (paise) out += ` and ${twoDigit(paise)} Paise`;
  return `${out} Only`;
}
