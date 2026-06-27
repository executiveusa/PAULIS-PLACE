'use client';

import { useEffect, useState, useRef } from 'react';
import { Brain, Cpu, DollarSign, Activity, Zap, MessageSquare, TrendingUp, Eye } from 'lucide-react';

const API_URL = '';
const WS_URL = typeof window !== 'undefined'
  ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
  : 'ws://localhost:8000/ws';

interface LogEntry {
  timestamp: number;
  task_type: string;
  model: string;
  tier: string;
  cost: number;
  input_tokens: number;
  output_tokens: number;
}

interface CouncilDelib {
  id: number;
  topic: string;
  status: string;
  problem_statement: string;
  ruling: string | null;
  total_cost: number;
  turns: number;
  created_at: string;
}

interface AgentCard {
  name: string;
  model: string;
  tier: string;
  color: string;
  active: boolean;
}

export default function ObservationPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [councilDelibs, setCouncilDelibs] = useState<CouncilDelib[]>([]);
  const [costs, setCosts] = useState<any>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [agents, setAgents] = useState<AgentCard[]>([
    { name: 'GLM-5.2', model: 'Strategist', tier: 'strategist', color: 'cyan', active: false },
    { name: 'DeepSeek', model: 'Workhorse', tier: 'workhorse', color: 'blue', active: false },
    { name: 'Ornith-1', model: 'Critic', tier: 'critic', color: 'purple', active: false },
    { name: 'Alpha-Owl', model: 'Evaluator', tier: 'critic', color: 'amber', active: false },
    { name: 'GLM-4', model: 'Grunt', tier: 'grunt', color: 'gray', active: false },
  ]);
  const consoleRef = useRef<HTMLDivElement>(null);

  // Fetch logs periodically
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const data = await fetch(`${API_URL}/api/research-lab/logs?limit=50`).then(r => r.json());
        if (data.logs) {
          setLogs(data.logs.reverse());
          // Update agent active states
          const recentModels = new Set(data.logs.slice(-10).map((l: LogEntry) => l.model));
          setAgents(prev => prev.map(a => ({
            ...a,
            active: recentModels.has(a.name)
          })));
        }
      } catch (e) {}
    };

    const fetchCosts = async () => {
      try {
        const data = await fetch(`${API_URL}/api/research-lab/costs`).then(r => r.json());
        setCosts(data);
      } catch (e) {}
    };

    fetchLogs();
    fetchCosts();
    const interval = setInterval(() => {
      fetchLogs();
      fetchCosts();
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket for real-time updates
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnect: NodeJS.Timeout | null = null;

    const connect = () => {
      ws = new WebSocket(WS_URL);
      ws.onopen = () => setWsConnected(true);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'log' || data.type === 'agent_activity') {
            setLogs(prev => [...prev.slice(-49), data.payload]);
          }
        } catch (e) {}
      };
      ws.onclose = () => {
        setWsConnected(false);
        reconnect = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      if (reconnect) clearTimeout(reconnect);
      ws?.close();
    };
  }, []);

  // Auto-scroll console
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs]);

  const colorMap: Record<string, string> = {
    cyan: 'border-cyan-400 shadow-cyan-400/30',
    blue: 'border-blue-400 shadow-blue-400/30',
    purple: 'border-purple-400 shadow-purple-400/30',
    amber: 'border-amber-400 shadow-amber-400/30',
    gray: 'border-gray-500 shadow-gray-500/20',
  };

  const activeColorMap: Record<string, string> = {
    cyan: 'bg-cyan-400/10 border-cyan-400 shadow-cyan-400/50 animate-pulse',
    blue: 'bg-blue-400/10 border-blue-400 shadow-blue-400/50 animate-pulse',
    purple: 'bg-purple-400/10 border-purple-400 shadow-purple-400/50 animate-pulse',
    amber: 'bg-amber-400/10 border-amber-400 shadow-amber-400/50 animate-pulse',
    gray: 'bg-gray-500/10 border-gray-400 shadow-gray-400/30 animate-pulse',
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <Eye className="w-7 h-7 text-cyan-400" />
            Observation Center
          </h1>
          <p className="text-gray-500 text-sm mt-1">PS4 Theater Mode - Real-time agent telemetry</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${wsConnected ? 'bg-green-400' : 'bg-red-400'} animate-pulse`} />
          <span className="text-xs text-gray-400">{wsConnected ? 'LIVE' : 'RECONNECTING'}</span>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4 h-[calc(100vh-140px)]">
        {/* Stage Left: Agent Roster */}
        <div className="col-span-3 space-y-3 overflow-auto">
          <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-2">Agent Roster</h2>
          {agents.map((agent) => (
            <div
              key={agent.name}
              className={`rounded-lg border p-4 transition-all duration-300 ${
                agent.active ? activeColorMap[agent.color] : `bg-gray-900/50 ${colorMap[agent.color]}`
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-sm">{agent.name}</div>
                  <div className="text-xs text-gray-500">{agent.model}</div>
                </div>
                <Cpu className={`w-5 h-5 ${agent.active ? 'animate-spin' : ''} text-gray-600`} />
              </div>
              {agent.active && (
                <div className="mt-2 text-xs text-cyan-400 flex items-center gap-1">
                  <Activity className="w-3 h-3" />
                  Thinking...
                </div>
              )}
            </div>
          ))}

          {/* Council indicator */}
          <div className="mt-6 rounded-lg border border-purple-500/30 bg-purple-500/5 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-purple-400">The Council</span>
            </div>
            <div className="text-xs text-gray-500">
              {councilDelibs.filter(d => d.status === 'deliberating').length > 0
                ? 'DELIBERATING...'
                : 'Standing by'}
            </div>
          </div>
        </div>

        {/* Center Stage: Terminal */}
        <div className="col-span-6 flex flex-col">
          <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-2">Agent Terminal</h2>
          <div
            ref={consoleRef}
            className="flex-1 bg-black/60 rounded-lg border border-gray-800 p-4 overflow-auto font-mono text-xs"
          >
            {logs.length === 0 ? (
              <div className="text-gray-600 text-center mt-20">
                Awaiting agent activity...
              </div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="mb-1 leading-relaxed">
                  <span className="text-gray-600">
                    [{new Date(log.timestamp * 1000).toLocaleTimeString()}]
                  </span>{' '}
                  <span className={tierColor(log.tier)}>
                    [{log.model}]
                  </span>{' '}
                  <span className="text-gray-300">{log.task_type}</span>{' '}
                  <span className="text-gray-600">
                    {log.input_tokens}+{log.output_tokens} tok
                  </span>{' '}
                  <span className="text-green-500">
                    ${log.cost.toFixed(5)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Stage Right: Telemetry */}
        <div className="col-span-3 space-y-4 overflow-auto">
          <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-2">Telemetry</h2>

          {/* Cost card */}
          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
            <div className="flex items-center gap-2 mb-3">
              <DollarSign className="w-4 h-4 text-green-400" />
              <span className="text-xs font-bold uppercase tracking-wider">API Spend</span>
            </div>
            <div className="text-3xl font-bold text-green-400">
              ${costs?.total_cost?.toFixed(4) || '0.0000'}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {costs?.call_count || 0} calls | avg ${(costs?.avg_cost_per_call || 0).toFixed(5)}
            </div>
          </div>

          {/* Model breakdown */}
          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold uppercase tracking-wider">By Model</span>
            </div>
            <div className="space-y-2">
              {Object.entries(costs?.by_model || {}).map(([model, cost]: [string, any]) => (
                cost > 0 && (
                  <div key={model} className="flex justify-between text-xs">
                    <span className="text-gray-400">{model}</span>
                    <span className="text-green-400">${cost.toFixed(4)}</span>
                  </div>
                )
              ))}
              {Object.values(costs?.by_model || {}).every((c: any) => c === 0) && (
                <div className="text-xs text-gray-600">No spend yet</div>
              )}
            </div>
          </div>

          {/* Daily limit */}
          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-xs font-bold uppercase tracking-wider">Daily Limit</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-green-400 to-amber-400"
                style={{ width: `${Math.min(100, ((costs?.total_cost || 0) / 5) * 100)}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 mt-2">
              ${(costs?.total_cost || 0).toFixed(2)} / $5.00
            </div>
          </div>
        </div>
      </div>

      {/* Lower Stage: The Council Arena */}
      <CouncilArena delibs={councilDelibs} />
    </div>
  );
}

function CouncilArena({ delibs }: { delibs: CouncilDelib[] }) {
  return (
    <div className="mt-4 rounded-lg border border-purple-500/20 bg-purple-500/5 p-4">
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare className="w-4 h-4 text-purple-400" />
        <span className="text-xs font-bold uppercase tracking-wider text-purple-400">Council Arena</span>
        <span className="text-xs text-gray-500 ml-auto">
          {delibs.length} deliberations on record
        </span>
      </div>
      {delibs.length === 0 ? (
        <div className="text-xs text-gray-600 text-center py-4">
          The Council stands in recess. No complex problems require debate.
        </div>
      ) : (
        <div className="space-y-2 max-h-32 overflow-auto">
          {delibs.slice(0, 5).map((d) => (
            <div key={d.id} className="flex items-center gap-3 text-xs">
              <span className={`w-2 h-2 rounded-full ${
                d.status === 'decided' ? 'bg-green-400' :
                d.status === 'deliberating' ? 'bg-amber-400 animate-pulse' :
                'bg-red-400'
              }`} />
              <span className="text-gray-400">#{d.id}</span>
              <span className="text-gray-300">{d.topic}</span>
              <span className="text-gray-600 ml-auto">${d.total_cost.toFixed(4)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function tierColor(tier: string): string {
  const map: Record<string, string> = {
    strategist: 'text-cyan-400',
    workhorse: 'text-blue-400',
    critic: 'text-purple-400',
    grunt: 'text-gray-400',
  };
  return map[tier] || 'text-gray-400';
}
