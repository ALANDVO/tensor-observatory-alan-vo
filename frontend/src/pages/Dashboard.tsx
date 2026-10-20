import { Cpu, Box, Database, TrendingUp, Clock, MemoryStick } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getHealth, getModels, getBenchmarks, getHardwareProfiles } from '../api/client';
import { Loading } from '../components/Loading';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';

const statCards = [
  { name: 'Models', key: 'models', icon: Box, color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30' },
  { name: 'Benchmarks', key: 'benchmarks', icon: Cpu, color: 'text-green-600 bg-green-50 dark:bg-green-900/30' },
  { name: 'Hardware', key: 'hardware', icon: Database, color: 'text-purple-600 bg-purple-50 dark:bg-purple-900/30' },
  { name: 'Health', key: 'health', icon: TrendingUp, color: 'text-orange-600 bg-orange-50 dark:bg-orange-900/30' },
];

export function Dashboard() {
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: getHealth });
  const { data: models, isLoading: modelsLoading } = useQuery({ queryKey: ['models'], queryFn: () => getModels({ limit: 1 }) });
  const { data: benchmarks, isLoading: benchmarksLoading } = useQuery({ queryKey: ['benchmarks'], queryFn: () => getBenchmarks({ limit: 1 }) });
  const { data: hardware, isLoading: hardwareLoading } = useQuery({ queryKey: ['hardware'], queryFn: getHardwareProfiles });

  const isLoading = modelsLoading || benchmarksLoading || hardwareLoading;

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <div key={card.key} className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 animate-pulse">
            <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded mb-2" />
            <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const stats = [
    { name: 'Models', value: models?.total || 0, icon: Box, color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30' },
    { name: 'Benchmarks', value: benchmarks?.total || 0, icon: Cpu, color: 'text-green-600 bg-green-50 dark:bg-green-900/30' },
    { name: 'Hardware Profiles', value: hardware?.length || 0, icon: Database, color: 'text-purple-600 bg-purple-50 dark:bg-purple-900/30' },
    { name: 'API Status', value: health?.status === 'healthy' ? 'Healthy' : 'Degraded', icon: TrendingUp, color: 'text-orange-600 bg-orange-50 dark:bg-orange-900/30' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Overview of your LLM inference observability platform</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.name} className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{stat.value}</p>
              </div>
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="h-6 w-6" aria-hidden="true" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Benchmarks</h2>
          {benchmarks?.items.length === 0 ? (
            <EmptyState
              title="No benchmarks yet"
              description="Run your first benchmark to see results here."
              actionLabel="Create Benchmark"
              onAction={() => window.location.href = '/benchmarks'}
              icon={<Cpu className="h-8 w-8" />}
            />
          ) : (
            <div className="space-y-3">
              {benchmarks.items.slice(0, 5).map((b) => (
                <div key={b.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                      <Cpu className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{b.name}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">{b.workload_type} • {b.status}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    b.status === 'completed' ? 'bg-green-100 text-green-700' :
                    b.status === 'running' ? 'bg-blue-100 text-blue-700' :
                    b.status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {b.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">System Health</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-300">API</span>
              <span className={`px-2 py-1 text-xs rounded-full ${
                health?.status === 'healthy' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>
                {health?.status || 'Unknown'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-300">Database</span>
              <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-700">Connected</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-300">Environment</span>
              <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                {health?.environment || 'Unknown'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}