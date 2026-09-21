import axios from 'axios';

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : '';
}

/** Kushnath website catalog API (dashboard app) — separate from Billvice /billing/api/ */
const storeApi = axios.create({
  baseURL: '/api/',
  withCredentials: true,
});

storeApi.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase();
  if (!['get', 'head', 'options'].includes(method)) {
    const csrf = readCookie('csrftoken');
    if (csrf) config.headers['X-CSRFToken'] = csrf;
  }
  // Let browser set multipart boundary when sending FormData
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

export const getWebsiteProducts = (params = {}) => storeApi.get('products/', { params });
export const getWebsiteProduct = (id) => storeApi.get(`products/${id}/`);
export const createWebsiteProduct = (data) => {
  if (data instanceof FormData) return storeApi.post('products/', data);
  return storeApi.post('products/', data);
};
export const updateWebsiteProduct = (id, data) => {
  if (data instanceof FormData) return storeApi.patch(`products/${id}/`, data);
  return storeApi.patch(`products/${id}/`, data);
};
export const deleteWebsiteProduct = (id) => storeApi.delete(`products/${id}/`);

export const getWebsiteCategories = () => storeApi.get('categories/');
export const createWebsiteCategory = (data) => {
  if (data instanceof FormData) return storeApi.post('categories/', data);
  return storeApi.post('categories/', data);
};
export const updateWebsiteCategory = (id, data) => {
  if (data instanceof FormData) return storeApi.patch(`categories/${id}/`, data);
  return storeApi.patch(`categories/${id}/`, data);
};
export const deleteWebsiteCategory = (id) => storeApi.delete(`categories/${id}/`);

export const uploadWebsiteProductImage = (productId, file) => {
  const fd = new FormData();
  fd.append('product', productId);
  fd.append('image', file);
  return storeApi.post('product-images/', fd);
};
export const deleteWebsiteProductImage = (id) => storeApi.delete(`product-images/${id}/`);

export function mediaUrl(path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  return path.startsWith('/') ? path : `/media/${path}`;
}
