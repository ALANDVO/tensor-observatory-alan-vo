import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Play, Trash2, Download, Eye, RotateCcw } from 'lucide-react';
import { getBenchmarks, createBenchmark, deleteBenchmark } from '../api/client';
import { getModels } from '../api/client';
import { Loading } from '../components/Loading';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { Benchmark, BenchmarkCreate, Model } from '../types/api';
import clsx from 'clsx';

const WORKLOAD_TYPES = [
  { value: 'synthetic', label: 'Synthetic (deterministic)' },
  { value: 'custom', label: 'Custom workload' },
] as const;

export function Benchmarks() {
  const queryClient = useQueryClient();
  const [modelFilter, setModelFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formData, setFormData] = useState<BenchmarkCreate>({
    model_id: 0,
    name: '',
    workload_type: 'synthetic',
    config_json: JSON.stringify({ batch_size: 8, seq_len: 2048, num_steps: 100 }, null, 2),
  });

  const { data: benchmarksData, isLoading, error } = useQuery({
    queryKey: ['benchmarks', { model_id: modelFilter, status: statusFilter, page }],
    queryFn: () => getBenchmarks({ model_id: modelFilter ? Number(modelFilter) : undefined, status: statusFilter, page, limit: 20 }),
  });

  const { data: modelsData } = useQuery({ queryKey: ['models-all'], queryFn: () => getModels({ limit: 1000 }) });
  const models = modelsData?.items || [];

  const createMutation = useMutation({
    mutationFn: createBenchmark,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmarks'] });
      setShowCreateModal(false);
      setFormData({ model_id: 0, name: '', workload_type: 'synthetic', config_json: JSON.stringify({ batch_size: 8, seq_len: 2048, num_steps: 100 }, null, 2) });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBenchmark,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['benchmarks'] }),
  });

  if (isLoading) {
    return <Loading className="py-12" />;
  }

  if (error) {
    return <ErrorState message="Failed to load benchmarks" onRetry={() => queryClient.invalidateQueries({ queryKey: ['benchmarks'] })} />;
  }

  const benchmarks = benchmarksData?.items || [];
  const total = benchmarksData?.total || 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.model_id || !formData.name) return;
    createMutation.mutate(formData);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Benchmarks</h1>
          <p className="text-gray-500 dark:text-gray-400">Run and track inference benchmarks</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Benchmark
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <select
            value={modelFilter}
            onChange={(e) => setModelFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Models</option>
            {models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Benchmarks Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        {benchmarks.length === 0 ? (
          <EmptyState
            title="No benchmarks found"
            description="Create your first benchmark to start measuring inference performance"
            actionLabel="New Benchmark"
            onAction={() => setShowCreateModal(true)}
            icon={<Play className="h-8 w-8" />}
            className="py-12"
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Model</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Workload</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Started</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Completed</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {benchmarks.map((b) => (
                    <tr key={b.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{b.name}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">Model #{b.model_id}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                          {b.workload_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx(
                          'px-2 py-1 text-xs rounded-full',
                          b.status === 'completed' && 'bg-green-100 text-green-700',
                          b.status === 'running' && 'bg-blue-100 text-blue-700',
                          b.status === 'failed' && 'bg-red-100 text-red-700',
                          b.status === 'pending' && 'bg-gray-100 text-gray-700',
                        )}>
                          {b.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{formatDate(b.started_at)}</td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{formatDate(b.completed_at)}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {b.status === 'completed' && (
                            <button className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors" title="View Results">
                              <Eye className="h-4 w-4" />
                            </button>
                          )}
                          {b.status === 'pending' && (
                            <button className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors" title="Run">
                              <Play className="h-4 w-4" />
                            </button>
                          )}
                          {b.status === 'failed' && (
                            <button className="p-2 text-gray-400 hover:text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded transition-colors" title="Retry">
                              <RotateCcw className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => deleteMutation.mutate(b.id)}
                            disabled={deleteMutation.isPending}
                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {total > 20 && (
              <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, total)} of {total}
                </p>
                <div className="flex gap-2">
                  <button onClick={() => setPage(p => p - 1)} disabled={page === 1} className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50">Previous</button>
                  <button onClick={() => setPage(p => p + 1)} disabled={page * 20 >= total} className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50">Next</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowCreateModal(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">Create Benchmark</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Model *</label>
                <select
                  value={formData.model_id}
                  onChange={e => setFormData({ ...formData, model_id: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                  required
                >
                  <option value={0}>Select a model</option>
                  {models.map(m => <option key={m.id} value={m.id}>{m.name} ({m.architecture}, {m.quantization})</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Workload Type</label>
                <select
                  value={formData.workload_type}
                  onChange={e => setFormData({ ...formData, workload_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
                >
                  {WORKLOAD_TYPES.map(w => <option key={w.value} value={w.value}>{w.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Configuration (JSON)</label>
                <textarea
                  value={formData.config_json}
                  onChange={e => setFormData({ ...formData, config_json: e.target.value })}
                  rows={8}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 font-mono text-sm"
                  placeholder='{"batch_size": 8, "seq_len": 2048, "num_steps": 100}'
                />
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