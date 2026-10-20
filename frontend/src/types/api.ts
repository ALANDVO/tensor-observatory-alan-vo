/** API types matching backend */

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  service: string;
  environment: string;
}

export interface UserInfo {
  user_id: string;
  email: string | null;
  name: string | null;
  roles: string[];
}

export interface Model {
  id: number;
  name: string;
  architecture: string | null;
  quantization: string | null;
  hardware_profile: string | null;
  huggingface_repo: string | null;
  description: string | null;
  config_json: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelCreate {
  name: string;
  architecture?: string;
  quantization?: string;
  hardware_profile?: string;
  huggingface_repo?: string;
  description?: string;
}

export interface Benchmark {
  id: number;
  model_id: number;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  workload_type: string;
  config_json: string;
  results_json: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BenchmarkCreate {
  model_id: number;
  name: string;
  workload_type: string;
  config_json: string;
}

export interface HardwareProfile {
  id: number;
  name: string;
  gpu_model: string;
  gpu_count: number;
  sm_version: string | null;
  vram_gb: number;
  driver_version: string | null;
  cuda_version: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Compatibility {
  id: number;
  model_id: number;
  hardware_id: number;
  status: 'compatible' | 'incompatible' | 'untested' | 'partial';
  notes: string | null;
  tested_at: string | null;
  tested_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}