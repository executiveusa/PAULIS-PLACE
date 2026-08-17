'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity, AlertTriangle, ArrowLeft, Cpu, Eye, Radio, ShieldCheck, Users } from 'lucide-react';
import { getSession, pauliControl, PauliOverview } from '@/lib/pauliControl';

export default function ObservationPage() {
  const [overview, setOverview] = useState<PauliOverview | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      if (!getSession()) throw new Error('AUTH_REQUIRED');
      setOverview(await pauliControl.overview());
      setError('');
    } catch (err) {
      setError(String(err).includes('AUTH_REQUIRED') ? 'Owner authentication required. Return to Mission Control to sign in.' : (err instanceof Error ? err.message : 'Control plane unavailable'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return (
    <div className="min-h-screen bg-[#080808] text-stone-100 p-6 lg:p-8">
      <div className="mx-auto max-w-7xl">
        <header className="flex items-center justify-between gap-5 border-b border-white/10 pb-6">
          <div className="flex items-center gap-4">
            <Link href="/" className="border border-white/10 p-2 text-stone-500 hover:text-white" aria-label="Back"><ArrowLeft className="h-4 w-4" /></Link>
            <div>
              <div className="text-[10px] uppercase tracking-[0.3em] text-amber-100/60">Truth surface</div>
              <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold"><Eye className="h-5 w-5" /> Observation</h1>
              <p className="mt-1 text-xs text-stone-500">Live missions, persistent agents, runtime providers, approvals, and incidents. No generated telemetry.</p>
            </div>
          </div>
          <button onClick={() => void refresh()} className="border border-white/10 px-4 py-2 text-xs text-stone-300 hover:border-amber-100/30">Refresh</button>
        </header>

        {error && <div className="mt-6 border border-red-400/20 bg-red-950/10 p-4 text-sm text-red-200">{error}</div>}

        <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Active missions" value={overview?.active_missions ?? 0} icon={Activity} />
          <Metric label="Agents working" value={overview?.agents_working ?? 0} icon={Users} />
          <Metric label="Approvals pending" value={overview?.approvals_pending ?? 0} icon={ShieldCheck} />
          <Metric label="Open incidents" value={overview?.open_incidents ?? 0} icon={AlertTriangle} />
        </section>

        <section className="mt-8 grid gap-8 xl:grid-cols-2">
          <div>
            <SectionTitle title="Persistent agents" subtitle="Identity is stable; models and compute are provider choices." />
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {(overview?.agents ?? []).map((agent) => (
                <div key={agent.id} className="border border-white/10 bg-[#0e0e0e] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div><div className="text-sm font-medium">{agent.name}</div><div className="text-xs text-stone-500">{agent.role}{agent.specialty ? ` · ${agent.specialty}` : ''}</div></div>
                    <Status status={agent.status} />
                  </div>
                  <div className="mt-4 flex items-center justify-between text-[10px] uppercase tracking-wider text-stone-600"><span>{agent.world_location_key || 'no world location'}</span><span>{agent.last_heartbeat_at ? new Date(agent.last_heartbeat_at).toLocaleTimeString() : 'no heartbeat'}</span></div>
                </div>
              ))}
              {!loading && !overview?.agents?.length && <Empty label="No agents registered." />}
            </div>
          </div>

          <div>
            <SectionTitle title="Runtime providers" subtitle="Unavailable providers remain visible rather than silently falling back." />
            <div className="mt-3 space-y-2">
              {(overview?.providers ?? []).map((provider) => (
                <div key={provider.provider_key} className="flex items-center justify-between gap-4 border border-white/10 bg-[#0e0e0e] p-4">
                  <div className="flex items-center gap-3"><Cpu className="h-4 w-4 text-stone-500" /><div><div className="text-sm font-medium">{provider.name}</div><div className="text-xs text-stone-500">{provider.kind} · {provider.provider_key}</div></div></div>
                  <Status status={provider.health_status} />
                </div>
              ))}
              {!loading && !overview?.providers?.length && <Empty label="No providers registered." />}
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-8 xl:grid-cols-[1.3fr_.7fr]">
          <div>
            <SectionTitle title="Mission stream" subtitle="Current durable outcomes and state transitions." />
            <div className="mt-3 divide-y divide-white/10 border border-white/10 bg-[#0e0e0e]">
              {(overview?.missions ?? []).map((mission) => (
                <div key={mission.id} className="flex items-center justify-between gap-5 p-4">
                  <div className="min-w-0"><div className="truncate text-sm font-medium">{mission.title}</div><div className="mt-1 line-clamp-1 text-xs text-stone-500">{mission.requested_outcome}</div></div>
                  <Status status={mission.status} />
                </div>
              ))}
              {!loading && !overview?.missions?.length && <Empty label="No active missions." />}
            </div>
          </div>

          <div>
            <SectionTitle title="Incident stream" subtitle="Operational blockers and recovery state." />
            <div className="mt-3 space-y-2">
              {(overview?.incidents ?? []).map((incident) => (
                <div key={incident.id} className="border border-red-400/20 bg-red-950/10 p-4">
                  <div className="flex items-center justify-between"><span className="text-[10px] uppercase tracking-wider text-red-300">{incident.severity}</span><Status status={incident.status} /></div>
                  <div className="mt-2 text-sm font-medium">{incident.title}</div>
                  <p className="mt-1 text-xs leading-5 text-stone-500">{incident.summary}</p>
                </div>
              ))}
              {!loading && !overview?.incidents?.length && <div className="flex items-center gap-2 border border-emerald-400/15 bg-emerald-950/10 p-4 text-xs text-emerald-300"><Radio className="h-3.5 w-3.5" /> No open incidents.</div>}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value, icon: Icon }: { label: string; value: number | string; icon: any }) { return <div className="border border-white/10 bg-[#0e0e0e] p-4"><Icon className="h-4 w-4 text-amber-100/60" /><div className="mt-5 text-2xl font-semibold">{value}</div><div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-stone-500">{label}</div></div>; }
function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) { return <div><h2 className="text-base font-medium">{title}</h2><p className="mt-1 text-xs text-stone-500">{subtitle}</p></div>; }
function Empty({ label }: { label: string }) { return <div className="border border-white/10 p-4 text-sm text-stone-600">{label}</div>; }
function Status({ status }: { status: string }) { const value = String(status || 'unknown').toLowerCase(); const good = ['ready','healthy','working','active','executing','verified','deployed','resolved'].some((item) => value.includes(item)); const bad = ['failed','error','blocked','critical','offline'].some((item) => value.includes(item)); const style = bad ? 'border-red-400/20 text-red-300' : good ? 'border-emerald-400/20 text-emerald-300' : 'border-white/10 text-stone-400'; return <span className={`border px-2 py-1 text-[10px] uppercase tracking-wider ${style}`}>{status || 'unknown'}</span>; }
