import axios from 'axios';

const API_BASE_URL = '/billing/api/';

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : '';
}

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase();
  if (!['get', 'head', 'options'].includes(method)) {
    const csrf = readCookie('csrftoken');
    if (csrf) config.headers['X-CSRFToken'] = csrf;
  }
  return config;
});

let onUnauthorized = null;
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = String(err.config?.url || '');
    if (err.response?.status === 401 && !url.includes('auth/')) {
      onUnauthorized?.();
    }
    return Promise.reject(err);
  }
);

export const ensureCsrf = () => api.get('auth/csrf/');
export const login = (data) => api.post('auth/login/', data);
export const logout = () => api.post('auth/logout/');
export const getMe = () => api.get('auth/me/');

export const getDashboardData = () => api.get('dashboard/');
export const getProducts = () => api.get('products/');
export const createProduct = (data) => api.post('products/', data);
export const updateProduct = (id, data) => api.put(`products/${id}/`, data);
export const deleteProduct = (id) => api.delete(`products/${id}/`);
export const getCategories = () => api.get('categories/');
export const createCategory = (data) => api.post('categories/', data);
export const deleteCategory = (id) => api.delete(`categories/${id}/`);
export const getStock = () => api.get('stock/');
export const getInvoices = () => api.get('invoices/');
export const getInvoiceDetail = (id) => api.get(`invoices/${id}/`);
export const createInvoicePos = (data) => api.post('pos/create-invoice/', data);
export const getCustomers = () => api.get('customers/');
export const createCustomer = (data) => api.post('customers/', data);
export const updateCustomer = (id, data) => api.put(`customers/${id}/`, data);
export const deleteCustomer = (id) => api.delete(`customers/${id}/`);
export const getCustomerLedger = (id) => api.get(`customers/${id}/ledger-data/`);
export const getDuesSummary = () => api.get('dues/summary/');
export const getPayments = () => api.get('payments/');
export const createPayment = (data) => api.post('payments/', data);
export const getPurchaseOrders = (params = '') => api.get(`purchase-orders/${params}`);
export const getPurchaseOrder = (id) => api.get(`purchase-orders/${id}/`);
export const createPurchaseOrder = (data) => api.post('purchase-orders/', data);
export const updatePurchaseOrder = (id, data) => api.put(`purchase-orders/${id}/`, data);
export const getPurchaseStats = () => api.get('purchase-orders/stats/');
export const placePurchaseOrder = (id) => api.post(`purchase-orders/${id}/place_order/`);
export const cancelPurchaseOrder = (id, data) => api.post(`purchase-orders/${id}/cancel/`, data);
export const duplicatePurchaseOrder = (id) => api.post(`purchase-orders/${id}/duplicate/`);
export const receivePurchaseOrder = (id, data) => api.post(`purchase-orders/${id}/receive/`, data);
export const getPendingReceipts = () => api.get('purchase-orders/pending_receipts/');
export const getPurchaseGstReport = (params = '') => api.get(`purchase-orders/gst_report/${params}`);
export const getSuppliers = () => api.get('suppliers/');
export const createSupplier = (data) => api.post('suppliers/', data);
export const updateSupplier = (id, data) => api.put(`suppliers/${id}/`, data);
export const deleteSupplier = (id) => api.delete(`suppliers/${id}/`);
export const getReportsSummary = () => api.get('reports/summary/');
export const getBalanceSheet = (asOf) => api.get('reports/balance-sheet/', { params: asOf ? { as_of: asOf } : {} });
export const getCompanySettings = () => api.get('settings/');
export const createCompanySettings = (data) => api.post('settings/', data);
export const updateCompanySettings = (id, data) => api.put(`settings/${id}/`, data);
export const globalSearch = (query) => api.get(`search/?q=${encodeURIComponent(query)}`);

// Raw Materials API
export const getRawMaterials = () => api.get('raw-materials/');
export const createRawMaterial = (data) => api.post('raw-materials/', data);
export const updateRawMaterial = (id, data) => api.put(`raw-materials/${id}/`, data);
export const deleteRawMaterial = (id) => api.delete(`raw-materials/${id}/`);
export const adjustRawMaterialStock = (id, data) => api.post(`raw-materials/${id}/adjust_stock/`, data);
export const getRawMaterialHistory = (id) => api.get(`raw-materials/${id}/history/`);

// Recipe / BOM API
export const getRecipes = () => api.get('recipes/');
export const saveRecipe = (data) => api.post('recipes/', data);

// Manufacturing API
export const getManufacturingLogs = (params) => api.get('manufacturing/', { params });
export const createManufacturingLog = (data) => api.post('manufacturing/', data);
export const updateManufacturingLog = (id, data) => api.patch(`manufacturing/${id}/`, data);
export const finalizeManufacturingLog = (id, data = {}) => api.post(`manufacturing/${id}/finalize/`, data);
export const deleteManufacturingLog = (id) => api.delete(`manufacturing/${id}/`);

// Stock Movements API
export const getStockMovements = () => api.get('stock-movements/');

// Invoice Cancellation
export const cancelInvoice = (id) => api.post(`invoices/${id}/cancel/`);

export default api;
