'use client';

import { useEffect, useMemo, useState } from 'react';
import { CircleAlert, Clock3, Filter, RefreshCw, ShieldCheck, Workflow } from 'lucide-react';
import { api, Mission } from '@/lib/api';
import { IntentComposer } from '@/components/IntentComposer';

const activeStates = new Set(['INTENT','UNDERSTOOD','PLANNED','STAFFED','PROVISIONED','EXECUTING','WAITING_APPROVAL','BLOCKED','RECOVERING','VERIFYING','DEPLOYED','OUTCOME_PENDING']);

export default function MissionsPage() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [status, setStatus] = useState('loading');
  const [filter, setFilter] = useState<'active'|'all'>('active');

  const load = async () => {
    setStatus('loading');
    try {
      const result = await api.controlPlane.missions('paulis-place', 100);
      setMissions(result.missions);
      setStatus(result.status);
    } catch {
      setMissions([]);
      setStatus('offline');
    }
  };

  useEffect(() => { load(); }, []);
  const visible = useMemo(() => filter === 'all' ? missions : missions.filter((m) => activeStates.has(m.status)), [missions, filter]);

  return (
    <div className="min-h-screen noir-grid px-4 py-5 md:px-8 md:py-8 lg:px-10">
      <div className="max-w-[1320px] mx-auto">
        <div className="flex items-start justify-between gap-4 mb-6">
          <div><div className="eyebrow">Mission Control</div><h1 className="text-2xl md:text-3xl font-semibold tracking-tight mt-1">Outcomes, not tickets</h1><p className="text-sm text-stone-500 mt-2 max-w-2xl">Every mission carries authority, budget, agents, evidence and a completion contract. “Done” means the requested outcome happened.</p></div>
          <button onClick={load} className="h-10 w-10 rounded-full border border-white/10 grid place-items-center text-stone-500 hover:text-white hover:bg-white/5"><RefreshCw className="w-4 h-4" /></button>
        </div>

        <IntentComposer compact onCreated={() => setTimeout(load, 200)} />

        <div className="mt-5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-stone-500"><span className={`status-dot ${status === 'ready' ? 'status-live' : 'status-warn'}`} />{status.replaceAll('_',' ')}</div>
          <div className="flex rounded-full border border-white/10 p-1 bg-black/20">
            {(['active','all'] as const).map((value) => <button key={value} onClick={() => setFilter(value)} className={`px-3 py-1.5 rounded-full text-xs capitalize ${filter === value ? 'bg-stone-100 text-stone-950 font-semibold' : 'text-stone-500'}`}>{value}</button>)}
          </div>
        </div>

        <div className="mt-4 space-y-3">
          {visible.length === 0 ? (
            <div className="pauli-panel min-h-[280px] grid place-items-center text-center p-8"><div><Workflow className="w-6 h-6 mx-auto text-stone-700 mb-3" /><p className="text-stone-400 text-sm">No {filter} missions.</p><p className="text-xs text-stone-600 mt-1">Give Pauli an intent above to create the first real mission.</p></div></div>
          ) : visible.map((mission) => <MissionCard key={mission.id} mission={mission} />)}
        </div>
      </div>
    </div>
  );
}

function MissionCard({ mission }: { mission: Mission }) {
  const needsHuman = mission.status === 'WAITING_APPROVAL';
  const blocked = mission.status === 'BLOCKED' || mission.status === 'FAILED';
  const pct = mission.autonomous_budget_cents > 0 ? Math.min(100, mission.spent_cents / mission.autonomous_budget_cents * 100) : 0;
  return (
    <article className="pauli-panel p-5 md:p-6">
      <div className="grid md:grid-cols-[1fr_auto] gap-5">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-2"><span className={`status-dot ${blocked ? 'status-bad' : needsHuman ? 'status-warn' : mission.status === 'OUTCOME_ACHIEVED' ? 'status-live' : ''}`} /><span className="text-[10px] uppercase tracking-[0.18em] text-stone-600">{mission.status.replaceAll('_',' ')}</span></div>
          <h2 className="text-lg font-semibold tracking-tight">{mission.title}</h2>
          <p className="text-sm text-stone-500 mt-2 max-w-3xl leading-relaxed">{mission.requested_outcome}</p>
        </div>
        <div className="md:text-right text-xs text-stone-600"><div>{new Date(mission.created_at).toLocaleString()}</div><div className="mt-1">{mission.language === 'es-MX' ? 'Mexican Spanish' : mission.language === 'mixed' ? 'Mixed language' : 'English'}</div></div>
      </div>
      <div className="grid sm:grid-cols-3 gap-3 mt-5 pt-4 border-t border-white/[0.065]">
        <Mini icon={ShieldCheck} label="Completion" value={mission.required_completion_level.replaceAll('_',' ')} />
        <Mini icon={Clock3} label="Attempts" value={String(mission.attempt_count)} />
        <div><div className="text-[10px] uppercase tracking-[0.16em] text-stone-700">Autonomy envelope</div><div className="flex items-center justify-between text-xs text-stone-400 mt-2"><span>${(mission.spent_cents/100).toFixed(2)} spent</span><span>${(mission.autonomous_budget_cents/100).toFixed(2)} max</span></div><div className="mt-2 h-1 rounded-full bg-white/[0.06] overflow-hidden"><div className="h-full bg-stone-400" style={{ width: `${pct}%` }} /></div></div>
      </div>
      {(needsHuman || blocked) && <div className={`mt-4 rounded-xl border p-3 text-xs flex items-start gap-2 ${needsHuman ? 'border-amber-500/15 bg-amber-500/[0.04] text-amber-100/70' : 'border-red-500/15 bg-red-500/[0.04] text-red-100/70'}`}><CircleAlert className="w-3.5 h-3.5 mt-0.5" />{needsHuman ? 'This mission is waiting for a consequential human approval.' : 'This mission is blocked. Pauli should exhaust materially different strategies within the approved envelope before escalating.'}</div>}
    </article>
  );
}

function Mini({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return <div><div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.16em] text-stone-700"><Icon className="w-3 h-3" />{label}</div><div className="text-xs text-stone-400 mt-2 capitalize">{value.toLowerCase()}</div></div>;
}
