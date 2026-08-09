'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowUpRight, BrainCircuit, Heart, MapPin, Radio, RefreshCw, Sparkles } from 'lucide-react';
import { api, PauliAgent } from '@/lib/api';

export default function AgentsPage() {
  const [agents, setAgents] = useState<PauliAgent[]>([]);
  const [status, setStatus] = useState('loading');

  const load = async () => {
    try {
      const result = await api.controlPlane.agents();
      setAgents(result.agents);
      setStatus(result.status);
    } catch {
      setAgents([]);
      setStatus('offline');
    }
  };
  useEffect(() => { load(); }, []);

  return (
    <div className="min-h-screen noir-grid px-4 py-5 md:px-8 md:py-8 lg:px-10">
      <div className="max-w-[1320px] mx-auto">
        <div className="flex items-start justify-between gap-4 mb-7">
          <div><div className="eyebrow">The crew</div><h1 className="text-2xl md:text-3xl font-semibold tracking-tight mt-1">Persistent people, interchangeable models</h1><p className="text-sm text-stone-500 mt-2 max-w-2xl">Each avatar keeps an identity, heart, soul, specialty and memory. The model underneath can change with the job without changing who the agent is.</p></div>
          <button onClick={load} className="h-10 w-10 rounded-full border border-white/10 grid place-items-center text-stone-500 hover:text-white hover:bg-white/5"><RefreshCw className="w-4 h-4" /></button>
        </div>

        <div className="flex items-center gap-2 text-xs text-stone-500 mb-5"><span className={`status-dot ${status === 'ready' ? 'status-live' : 'status-warn'}`} />{status.replaceAll('_',' ')}</div>

        {agents.length === 0 ? (
          <div className="pauli-panel min-h-[360px] grid place-items-center text-center p-8"><div><Sparkles className="w-7 h-7 mx-auto text-stone-700 mb-3" /><p className="text-sm text-stone-400">The Pauli roster has not been bootstrapped in the control-plane database yet.</p><p className="text-xs text-stone-600 mt-2 max-w-lg">The schema is ready for identity, heart, soul, persona memory, skills, runtime policy and world location. No placeholder agents are shown here.</p></div></div>
        ) : (
          <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {agents.map((agent) => <AgentCard key={agent.id} agent={agent} />)}
          </div>
        )}

        <div className="pauli-panel p-5 mt-5 grid md:grid-cols-3 gap-5 text-xs text-stone-500">
          <Principle icon={Heart} title="Identity persists" body="HEART, SOUL and persona memory belong to the agent, not the model provider." />
          <Principle icon={BrainCircuit} title="AutoModel routes" body="Pauli can choose local, open or frontier reasoning based on capability, privacy, latency, cost and policy." />
          <Principle icon={Radio} title="Observable" body="Heartbeat, mission, runtime and location state drive the 2D and 3D interfaces instead of synthetic animation." />
        </div>
      </div>
    </div>
  );
}

function AgentCard({ agent }: { agent: PauliAgent }) {
  const active = ['working','meeting','recovering'].includes(agent.status);
  const blocked = ['blocked','error','waiting_approval'].includes(agent.status);
  return (
    <article className="pauli-panel p-5 group">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-12 w-12 rounded-2xl border border-white/10 bg-stone-100 text-stone-950 grid place-items-center font-black text-lg shadow-[0_0_30px_rgba(255,255,255,.05)]">{agent.name.slice(0,1).toUpperCase()}</div>
          <div className="min-w-0"><h2 className="font-semibold truncate">{agent.name}</h2><p className="text-xs text-stone-600 truncate mt-0.5">{agent.role}</p></div>
        </div>
        <span className={`status-dot ${active ? 'status-live' : blocked ? 'status-warn' : ''}`} />
      </div>
      <p className="text-sm text-stone-400 mt-5 min-h-[42px]">{agent.specialty || 'General autonomous support'}</p>
      <div className="mt-5 pt-4 border-t border-white/[0.065] grid grid-cols-2 gap-3 text-[11px]">
        <div><div className="text-stone-700 uppercase tracking-[.14em]">State</div><div className="text-stone-400 mt-1 capitalize">{agent.status.replaceAll('_',' ')}</div></div>
        <div><div className="text-stone-700 uppercase tracking-[.14em]">Location</div><div className="text-stone-400 mt-1 flex items-center gap-1"><MapPin className="w-3 h-3" />{agent.world_location_key || 'not placed'}</div></div>
      </div>
      <Link href="/lounge" className="mt-5 flex items-center justify-between rounded-xl bg-white/[0.035] border border-white/[0.065] px-3.5 py-2.5 text-xs text-stone-500 group-hover:text-stone-200 group-hover:border-white/15 transition"><span>Go talk to {agent.name}</span><ArrowUpRight className="w-3.5 h-3.5" /></Link>
    </article>
  );
}

function Principle({ icon: Icon, title, body }: { icon: any; title: string; body: string }) {
  return <div className="flex items-start gap-3"><div className="h-8 w-8 rounded-lg border border-white/10 grid place-items-center shrink-0"><Icon className="w-3.5 h-3.5 text-stone-500" /></div><div><div className="text-stone-300 font-medium">{title}</div><p className="mt-1 leading-relaxed text-stone-600">{body}</p></div></div>;
}
