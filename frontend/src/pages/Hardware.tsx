import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Cpu, MemoryStick, Zap } from 'lucide-react';
import { getHardwareProfiles, createHardwareProfile } from '../api/client';
import { Loading } from '../components/Loading';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { HardwareProfile } from '../types/api';

export function Hardware() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formData, setFormData] = useState<Omit<HardwareProfile, 'id' | 'created_at' | 'updated_at'>>({
    name: '',
    gpu_model: '',
    gpu_count: 1,
    sm_version: '',
    vram_gb: 0,
    driver_version: '',
    cuda_version: '',
    notes: '',
  });

  const { data, isLoading, error } = useQuery({ queryKey: ['hardware'], queryFn: getHardwareProfiles });

  const createMutation = useMutation({
    mutationFn: createHardwareProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hardware'] });
      setShowCreateModal(false);
      setFormData({ name: '', gpu_model: '', gpu_count: 1, sm_version: '', vram_gb: 0, driver_version: '', cuda_version: '', notes: '' });
    },
  });

  if (isLoading) return <Loading className="py-12" />;
  if (error) return <ErrorState message="Failed to load hardware profiles" onRetry={() => queryClient.invalidateQueries({ queryKey: ['hardware'] })} />;

  const hardware = data || [];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.gpu_model || !formData.vram_gb) return;
    createMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Hardware Profiles</h1>
          <p className="text-gray-500 dark:text-gray-400">Manage GPU hardware configurations for compatibility tracking</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
          <Plus className="h-4 w-4" /> Add Hardware
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {hardware.length === 0 ? (
          <EmptyState
            title="No hardware profiles"
            description="Add your first GPU configuration to track model compatibility"
            actionLabel="Add Hardware"
            onAction={() => setShowCreateModal(true)}
            icon={<Cpu className="h-8 w-8" />}
            className="lg:col-span-3 py-12"
          />
        ) : (
          hardware.map((hw) => (
            <div key={hw.id} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">{hw.name}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{hw.gpu_model} × {hw.gpu_count}</p>
                </div>
                <button onClick={() => {}} className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors" title="Delete">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                  <MemoryStick className="h-4 w-4 text-primary-600" />
                  <span>{hw.vram_gb} GB VRAM per GPU</span>
                </div>
                {hw.sm_version && (
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                    <Zap className="h-4 w-4 text-yellow-600" />
                    <span>SM {hw.sm_version}</span>
                  </div>
                )}
                {hw.driver_version && (
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                    <span>Driver: {hw.driver_version}</span>
                  </div>
                )}
                {hw.cuda_version && (
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                    <span>CUDA: {hw.cuda_version}</span>
                  </div>
                )}
                {hw.notes && (
                  <div className="text-gray-500 dark:text-gray-400 italic">{hw.notes}</div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowCreateModal(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">Add Hardware Profile</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name *</label>
                <input type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500" required placeholder="e.g., A100-80GB-8x" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">GPU Model *</label>
                <input type="text" value={formData.gpu_model} onChange={e => setFormData({...formData, gpu_model: e.target.value})} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500" required placeholder="e.g., A100" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">GPU Count</label>
                  <input type="number" value={formData.gpu_count} onChange={e => setFormData({...formData, gpu_count: Number(e.target.value)})} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500" min={1} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">VRAM (GB) *</label>
                  <input type="number" value={formData.vram_gb} onChange={e => setFormData({...formData, vram_gb: Number(e.target.value)})} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500" min={1} required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">SM Version</label>
                  <input type="text" value={formData.sm_version} onChange={e => setFormData({...formData, sm_version: e.target.value})} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500" placeholder="e.g., 8.0" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">CUDA Version</label>
                  <input type="text" value={formData.cuda_version} onChange={e => setFormData({...formData, cuda_version: e.target.value})} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500" placeholder="e.g., 12.4" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Driver Version</label>
                <input type="text" value={formData.driver_version} onChange={e => setFormData({...formData, driver_version: e.target.value})} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500" placeholder="e.g., 550.54" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea value={formData.notes} onChange={e => setFormData({...formData, notes: e.target.value})} rows={3} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500" />
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">Cancel</button>
                <button type="submit" disabled={createMutation.isPending} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{createMutation.isPending ? 'Creating...' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}