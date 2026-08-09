'use client';

import dynamic from 'next/dynamic';
import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, ArrowLeft, Clapperboard, Mic, Radio, User, Users } from 'lucide-react';
import Link from 'next/link';
import { api, PauliAgent } from '@/lib/api';
import { lounge as loungeApi, Envelope, DEMO_ENABLED } from '@/lib/loungeApi';
import { useVoiceCommand } from './useVoiceCommand';
import type { WorldMode } from './ThreeScene';

const ThreeScene = dynamic(() => import('./ThreeScene'), { ssr: false });

export default function LoungeClient() {
  const [agents, setAgents] = useState<PauliAgent[]>([]);
  const [selected, setSelected] = useState<PauliAgent | null>(null);
  const [scenes, setScenes] = useState<Envelope[]>([]);
  const [mode, setMode] = useState<WorldMode>('live');
  const [backendStatus, setBackendStatus] = useState<'checking'|'live'|'offline'>('checking');

  const load = async () => {
    try {
      const response = await api.controlPlane.agents();
      setAgents(response.agents);
      setSelected((current) => current || response.agents.find(a => a.agent_key === 'pauli') || response.agents[0] || null);
      setBackendStatus('live');
    } catch {
      setAgents([]);
      setSelected(null);
      setBackendStatus('offline');
    }
    loungeApi.scenes(16).then(r => setScenes(r.scenes)).catch(() => {});
  };

  useEffect(() => {
    load();
    const poll = setInterval(load, 15000);
    const wsUrl = process.env.NEXT_PUBLIC_LOUNGE_WS_URL || process.env.NEXT_PUBLIC_WS_URL;
    let ws: WebSocket | undefined;
    if (wsUrl) {
      try {
        ws = new WebSocket(wsUrl);
        ws.onmessage = (message) => {
          try {
            const data = JSON.parse(message.data);
            if (data?.type === 'event' && data.envelope) {
              setScenes(prev => [data.envelope, ...prev].slice(0, 16));
              setBackendStatus('live');
            }
          } catch {}
        };
      } catch {}
    }
    return () => { clearInterval(poll); ws?.close(); };
  }, []);

  const onAccept = (env: Envelope) => setScenes(prev => [env, ...prev].slice(0, 16));
  const { listening, transcript, error, lastResponse, start, stop } = useVoiceCommand({ onAccept });
  const activeAgents = useMemo(() => agents.filter(a => ['working','meeting','recovering'].includes(a.status)).length, [agents]);

  return (
    <div className="min-h-screen bg-[#080807] text-stone-100 flex flex-col">
      <header className="relative z-20 border-b border-white/[0.08] bg-[#090908]/88 backdrop-blur-xl px-4 md:px-6 py-3.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0"><Link href="/" className="h-9 w-9 shrink-0 rounded-full border border-white/10 grid place-items-center text-stone-500 hover:text-white hover:bg-white/5"><ArrowLeft className="w-4 h-4" /></Link><div className="min-w-0"><div className="eyebrow">Pauli's World</div><div className="text-sm font-semibold truncate mt-1">Pauli's Place · Seattle after hours</div></div></div>
        <div className="flex items-center gap-2">
          <div className="hidden sm:flex rounded-full border border-white/10 p-1 bg-black/30"><button onClick={() => setMode('live')} className={`px-3 py-1.5 rounded-full text-[11px] flex items-center gap-1.5 ${mode === 'live' ? 'bg-stone-100 text-stone-950 font-semibold' : 'text-stone-500'}`}><Radio className="w-3 h-3" />Live</button><button onClick={() => setMode('director')} className={`px-3 py-1.5 rounded-full text-[11px] flex items-center gap-1.5 ${mode === 'director' ? 'bg-stone-100 text-stone-950 font-semibold' : 'text-stone-500'}`}><Clapperboard className="w-3 h-3" />Director cut</button></div>
          <button onClick={listening ? stop : start} className={`h-9 px-3.5 rounded-full border text-xs font-medium flex items-center gap-2 transition ${listening ? 'bg-red-500 border-red-400 text-white animate-pulse' : 'border-white/10 bg-white/[0.04] text-stone-300 hover:bg-white/[0.08]'}`}><Mic className="w-3.5 h-3.5" />{listening ? 'Listening…' : `Talk${selected ? ` to ${selected.name}` : ''}`}</button>
        </div>
      </header>

      <main className="flex-1 grid xl:grid-cols-[1fr_330px] min-h-0">
        <section className="relative min-h-[540px] xl:min-h-[calc(100vh-65px)] overflow-hidden">
          <ThreeScene agents={agents} selectedAgentId={selected?.id} onSelectAgent={setSelected} mode={mode} />
          <div className="absolute bottom-4 left-4 right-4 md:right-auto md:w-[430px] z-10 pauli-panel p-4 bg-black/70">
            <div className="flex items-start justify-between gap-4"><div className="min-w-0"><div className="flex items-center gap-2"><span className={`status-dot ${backendStatus === 'live' ? 'status-live' : backendStatus === 'offline' ? 'status-bad' : 'status-warn'}`} /><span className="eyebrow !tracking-[.14em]">{backendStatus === 'live' ? 'Real control-plane state' : 'Control plane unavailable'}</span></div><div className="mt-2 text-sm font-medium">{selected ? `${selected.name} · ${selected.role}` : 'Click an avatar to talk directly'}</div><div className="text-xs text-stone-500 mt-1.5 leading-relaxed">{selected?.specialty || 'Avatars appear only when registered in the Pauli control plane. Their movement is presentation; their work status comes from real agent state.'}</div></div>{selected && <div className="text-[10px] uppercase tracking-[.15em] text-stone-600 capitalize whitespace-nowrap">{selected.status.replaceAll('_',' ')}</div>}</div>
            {transcript && <div className="mt-3 pt-3 border-t border-white/[0.07] text-xs text-stone-300"><span className="text-stone-600">You:</span> {transcript}</div>}
            {error && <div className="mt-3 text-xs text-red-300 flex items-start gap-2"><AlertCircle className="w-3.5 h-3.5 mt-0.5" />{error}</div>}
            {lastResponse?.halt && <div className="mt-3 text-xs text-amber-200">Guardian stopped that action before execution.</div>}
          </div>
        </section>

        <aside className="hidden xl:flex border-l border-white/[0.07] bg-[#0a0a09] flex-col min-h-0">
          <div className="p-5 border-b border-white/[0.06]"><div className="eyebrow">The room</div><div className="grid grid-cols-2 gap-2 mt-4"><Metric icon={Users} value={agents.length} label="agents here" /><Metric icon={Radio} value={activeAgents} label="working" /></div>{DEMO_ENABLED && <div className="mt-3 rounded-xl border border-amber-500/15 bg-amber-500/[0.04] px-3 py-2 text-[10px] text-amber-200/70">Explicit demo mode is enabled.</div>}</div>
          <div className="p-5 flex-1 overflow-y-auto scrollbar-thin"><div className="flex items-center justify-between"><div className="eyebrow">Live scene feed</div><span className="text-[10px] text-stone-700">truth layer</span></div><div className="mt-4 space-y-2">{scenes.length === 0 && <div className="rounded-xl border border-dashed border-white/[0.08] px-4 py-7 text-center"><User className="w-4 h-4 mx-auto text-stone-700 mb-2" /><div className="text-xs text-stone-500">No real scene events yet.</div><div className="text-[10px] text-stone-700 mt-1">Nothing is invented to make the room look busy.</div></div>}{scenes.map(scene => <SceneCard key={`${scene.event_id}:${scene.ts}`} scene={scene} />)}</div></div>
        </aside>
      </main>
    </div>
  );
}

function Metric({ icon: Icon, value, label }: { icon:any; value:number; label:string }) { return <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-3"><Icon className="w-3.5 h-3.5 text-stone-700" /><div className="text-xl font-semibold mt-3">{value}</div><div className="text-[10px] text-stone-600 mt-1">{label}</div></div>; }
function SceneCard({ scene }: { scene: Envelope }) { const summary = scene.body?.response_text || scene.body?.lounge_scene_intent || scene.body?.celebration_intent || scene.next_action || `${scene.route} · ${scene.stage}`; return <div className="rounded-xl border border-white/[0.06] bg-black/25 p-3"><div className="text-[9px] uppercase tracking-[.15em] text-stone-700">{scene.route} · {scene.stage}</div><div className="text-xs text-stone-400 mt-1.5 leading-relaxed line-clamp-3">{String(summary)}</div><div className="text-[9px] text-stone-700 mt-2">{scene.ts}</div></div>; }
