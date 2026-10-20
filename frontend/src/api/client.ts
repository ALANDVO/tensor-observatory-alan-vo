import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { Model, ModelCreate, Benchmark, BenchmarkCreate, HardwareProfile, Compatibility, UserInfo } from '../types/api';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// CSRF token handling
let csrfToken: string | null = null;

export function setCsrfToken(token: string) {
  csrfToken = token;
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method || '')) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear auth state
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Health
export async function getHealth() {
  const { data } = await api.get<{ status: string; service: string; environment: string }>('/health');
  return data;
}

export async function getHealthDb() {
  const { data } = await api.get<{ status: string; database: string; error?: string }>('/health/db');
  return data;
}

// Auth
export async function getMe(): Promise<UserInfo | null> {
  try {
    const { data } = await api.get<UserInfo>('/auth/me');
    return data;
  } catch (e) {
    return null;
  }
}

export async function getCsrfToken() {
  const { data } = await api.get<{ csrf_token: string }>('/auth/csrf');
  setCsrfToken(data.csrf_token);
  return data.csrf_token;
}

export function login() {
  window.location.href = `${API_BASE}/auth/login`;
}

export async function logout() {
  await api.post('/auth/logout');
  window.location.href = '/login';
}

// Models
export async function getModels(params?: { search?: string; architecture?: string; quantization?: string; page?: number; limit?: number }) {
  const { data } = await api.get<{ items: Model[]; total: number; page: number; limit: number }>('/models', { params });
  return data;
}

export async function getModel(id: number) {
  const { data } = await api.get<Model>(`/models/${id}`);
  return data;
}

export async function createModel(model: ModelCreate) {
  const { data } = await api.post<Model>('/models', model);
  return data;
}

export async function updateModel(id: number, model: Partial<ModelCreate>) {
  const { data } = await api.patch<Model>(`/models/${id}`, model);
  return data;
}

export async function deleteModel(id: number) {
  await api.delete(`/models/${id}`);
}

export async function importModelFromHuggingFace(repo: string) {
  const { data } = await api.post<Model>('/models/import', { huggingface_repo: repo });
  return data;
}

// Benchmarks
export async function getBenchmarks(params?: { model_id?: number; status?: string; page?: number; limit?: number }) {
  const { data } = await api.get<{ items: Benchmark[]; total: number; page: number; limit: number }>('/benchmarks', { params });
  return data;
}

export async function getBenchmark(id: number) {
  const { data } = await api.get<Benchmark>(`/benchmarks/${id}`);
  return data;
}

export async function createBenchmark(benchmark: BenchmarkCreate) {
  const { data } = await api.post<Benchmark>('/benchmarks', benchmark);
  return data;
}

export async function deleteBenchmark(id: number) {
  await api.delete(`/benchmarks/${id}`);
}

// Hardware
export async function getHardwareProfiles() {
  const { data } = await api.get<HardwareProfile[]>('/hardware');
  return data;
}

export async function createHardwareProfile(profile: Omit<HardwareProfile, 'id' | 'created_at' | 'updated_at'>) {
  const { data } = await api.post<HardwareProfile>('/hardware', profile);
  return data;
}

// Compatibility
export async function getCompatibility(params?: { model_id?: number; hardware_id?: number }) {
  const { data } = await api.get<Compatibility[]>('/compatibility', { params });
  return data;
}

export async function createCompatibility(compat: Omit<Compatibility, 'id' | 'created_at' | 'updated_at'>) {
  const { data } = await api.post<Compatibility>('/compatibility', compat);
  return data;
}

export default api;