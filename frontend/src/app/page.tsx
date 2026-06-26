'use client';

import { useEffect, useState } from 'react';
import { api, DashboardStats } from '@/lib/api';
import {
  Package,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Play,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import { RevenueChart } from '@/components/RevenueChart';
import { AgentStatus } from '@/components/AgentStatus';

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const data = await api.dashboard.getStats();
      setStats(data);
    } catch (e) {
      console.error('Failed to load stats');
    } finally {
      setLoading(false);
    }
  };

  const triggerAction = async (action: 'scanTrends' | 'scoreTrends' | 'createProducts') => {
    setTriggering(action);
    try {
      await api.triggers[action]();
      setTimeout(loadStats, 2000);
    } catch (e) {
      console.error('Trigger failed');
    } finally {
      setTriggering(null);
    }
  };

  if (loading || !stats) {
    return <div className="p-8 text-gray-400">Loading...</div>;
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-400 mt-1">Autonomous product factory overview</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => triggerAction('scanTrends')}
            disabled={triggering !== null}
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${triggering === 'scanTrends' ? 'animate-spin' : ''}`} />
            Scan Trends
          </button>
          <button
            onClick={() => triggerAction('createProducts')}
            disabled={triggering !== null}
            className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <Play className={`w-4 h-4 ${triggering === 'createProducts' ? 'animate-pulse' : ''}`} />
            Create Products
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Products"
          value={stats.products.total}
          subtitle={`${stats.products.published} published`}
          icon={Package}
          color="blue"
        />
        <StatCard
          title="Total Revenue"
          value={`$${stats.revenue.total.toFixed(2)}`}
          subtitle={`${stats.revenue.total_sales} sales`}
          icon={DollarSign}
          color="green"
        />
        <StatCard
          title="7-Day Revenue"
          value={`$${stats.revenue.last_7_days.toFixed(2)}`}
          subtitle="Last 7 days"
          icon={TrendingUp}
          color="purple"
          change={12.5}
        />
        <StatCard
          title="Pending Approval"
          value={stats.products.pending_approval}
          subtitle="Needs your review"
          icon={AlertTriangle}
          color="yellow"
        />
      </div>

      {/* Charts and Agent Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-gray-900 rounded-xl border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Revenue Trend</h2>
          <RevenueChart />
        </div>
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Agent Status</h2>
          <AgentStatus
            running={stats.tasks.running}
            failed={stats.tasks.failed}
          />
        </div>
      </div>

      {/* Platform Breakdown */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Revenue by Platform</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {Object.entries(stats.revenue.by_platform).map(([platform, data]) => (
            <div key={platform} className="bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-400 capitalize">{platform}</div>
              <div className="text-2xl font-bold mt-1">${data.revenue.toFixed(2)}</div>
              <div className="text-sm text-gray-500 mt-1">{data.count} products</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  change
}: {
  title: string;
  value: string | number;
  subtitle: string;
  icon: any;
  color: string;
  change?: number;
}) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-500/10 text-blue-400',
    green: 'bg-green-500/10 text-green-400',
    purple: 'bg-purple-500/10 text-purple-400',
    yellow: 'bg-yellow-500/10 text-yellow-400',
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
      <div className="flex items-center justify-between">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        {change !== undefined && (
          <div className={`flex items-center gap-1 text-sm ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {change >= 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
            {change}%
          </div>
        )}
      </div>
      <div className="mt-4">
        <div className="text-2xl font-bold">{value}</div>
        <div className="text-sm text-gray-400 mt-1">{subtitle}</div>
      </div>
      <div className="text-xs text-gray-500 mt-2">{title}</div>
    </div>
  );
}
