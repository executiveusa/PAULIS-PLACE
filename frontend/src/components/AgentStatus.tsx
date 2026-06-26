'use client';

import { useEffect, useState } from 'react';
import { api, TaskSummary } from '@/lib/api';
import { Activity, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

interface AgentStatusProps {
  running: number;
  failed: number;
}

export function AgentStatus({ running, failed }: AgentStatusProps) {
  const [taskSummary, setTaskSummary] = useState<TaskSummary>({});

  useEffect(() => {
    api.tasks.summary().then(setTaskSummary);
    const interval = setInterval(() => api.tasks.summary().then(setTaskSummary), 10000);
    return () => clearInterval(interval);
  }, []);

  const agents = [
    { name: 'Trend Scanner', type: 'trend_scan' },
    { name: 'Research Agent', type: 'research' },
    { name: 'Design Agent', type: 'design_generation' },
    { name: 'Copy Writer', type: 'copy_generation' },
    { name: 'Listing Agent', type: 'listing_creation' },
  ];

  return (
    <div className="space-y-3">
      {agents.map((agent) => {
        const tasks = taskSummary[agent.type] || {};
        const isRunning = (tasks.running || 0) > 0;
        const hasFailed = (tasks.failed || 0) > 0;
        const completed = tasks.completed || 0;

        return (
          <div key={agent.type} className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              {isRunning ? (
                <Loader2 className="w-4 h-4 text-brand-500 animate-spin" />
              ) : hasFailed ? (
                <AlertCircle className="w-4 h-4 text-red-400" />
              ) : (
                <CheckCircle className="w-4 h-4 text-green-400" />
              )}
              <span className="text-sm">{agent.name}</span>
            </div>
            <div className="text-xs text-gray-500">
              {isRunning ? 'Running' : `${completed} completed`}
            </div>
          </div>
        );
      })}

      {running > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="flex items-center gap-2 text-sm text-brand-500">
            <Activity className="w-4 h-4" />
            {running} tasks running
          </div>
        </div>
      )}

      {failed > 0 && (
        <div className="mt-2">
          <div className="flex items-center gap-2 text-sm text-red-400">
            <AlertCircle className="w-4 h-4" />
            {failed} failed tasks
          </div>
        </div>
      )}
    </div>
  );
}
