'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowLeft, Radio, WifiOff } from 'lucide-react';
import { council as councilApi, lounge as loungeApi, Envelope, LoungeState, PortfolioDecision } from '@/lib/loungeApi';
import { fetchPauliverseSnapshot, PauliverseSnapshot } from '@/lib/pauliverseApi';
import { useVoiceCommand } from './useVoiceCommand';

const ThreeScene = dynamic(() => import('./ThreeScene'), { ssr: false });
const CommandWorld = dynamic(() => import('./CommandWorld'), { ssr: false });
const CouncilChamber = dynamic(() => import('./CouncilChamber'), { ssr: false });

const EMPTY_STATE: LoungeState = {
  lounge: "Pauli's Place",
  setting: 'Operational world · canonical backend state only',
  avatars: [],
  schedule_cue: 'Waiting for canonical world state',
  source: 'pauli.control_plane',
  status: 'unavailable',
};

type WorldMode = 'portfolio' | 'council' | 'agents';

export default function LoungeClient() {
  const [mode, setMode] = useState<WorldMode>('portfolio');
  const [state, setState] = useState<LoungeState>(EMPTY_STATE);
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [scenes, setScenes] = useState<Envelope[]>([]);
  const [decisions, setDecisions] = useState<PortfolioDecision[]>([]);
  const [speaker, setSpeaker] = useState<string | null>(null);
  const [worldError, setWorldError] = useState('');
  const [councilError, setCouncilError] = useState('');
  const [portfolio, setPortfolio] = useState<PauliverseSnapshot | null>(null);
  const [portfolioError, setPortfolioError] = useState('');

  const refreshWorldState = async () => {
    try {
      const next = await loungeApi.state();
      setState(next);
      setBackendUp(true);
      setWorldError(next.status && next.status !== 'ready' ? next.schedule_cue : '');
    } catch (error) {
      setBackendUp(false);
      setWorldError(error instanceof Error ? error.message : 'World backend unavailable');
      setState(EMPTY_STATE);
    }
  };

  const onAccept = (env: Envelope) => {
    setScenes((current) => [env, ...current].slice(0, 16));
    const target = env?.body?.target_avatar || env?.body?.agent_id;
    if (target) {
      setSpeaker(target);
      window.setTimeout(() => setSpeaker(null), 3500);
    }
    void refreshWorldState();
  };

  const { listening, transcript, error, lastResponse, start, stop } = useVoiceCommand({ onAccept });

  useEffect(() => {
    let cancelled = false;

    const refreshPortfolio = async () => {
      try {
        const snapshot = await fetchPauliverseSnapshot();
        if (cancelled) return;
        setPortfolio(snapshot);
        setPortfolioError('');
      } catch (err) {
        if (cancelled) return;
        setPortfolio(null);
        setPortfolioError(err instanceof Error ? err.message : 'Portfolio snapshot unavailable');
      }
    };

    const refreshAgents = async () => {
      try {
        const next = await loungeApi.state();
        if (cancelled) return;
        setState(next);
        setBackendUp(true);
        setWorldError(next.status && next.status !== 'ready' ? next.schedule_cue : '');
      } catch (err) {
        if (cancelled) return;
        setBackendUp(false);
        setWorldError(err instanceof Error ? err.message : 'World backend unavailable');
        setState(EMPTY_STATE);
      }
    };

    const refreshScenes = async () => {
      try {
        const result = await loungeApi.scenes(16);
        if (!cancelled) setScenes(result.scenes);
      } catch {
        if (!cancelled) setScenes([]);
      }
    };

    const refreshCouncil = async () => {
      try {
        const result = await councilApi.portfolioDeliberations(12);
        if (cancelled) return;
        setDecisions(result.deliberations);
        setCouncilError('');
      } catch (err) {
        if (cancelled) return;
        setDecisions([]);
        setCouncilError(err instanceof Error ? err.message : 'Council evidence unavailable');
      }
    };

    void refreshPortfolio();
    void refreshAgents();
    void refreshScenes();
    void refreshCouncil();

    const poll = window.setInterval(() => {
      void refreshAgents();
      void refreshPortfolio();
    }, 15000);

    const wsUrl = process.env.NEXT_PUBLIC_LOUNGE_WS_URL || process.env.NEXT_PUBLIC_WS_URL;
    let ws: WebSocket | undefined;
    if (wsUrl) {
      try {
        ws = new WebSocket(wsUrl);
        ws.onopen = () => { if (!cancelled) setBackendUp(true); };
        ws.onerror = () => { if (!cancelled) setBackendUp(false); };
        ws.onmessage = (message) => {
          try {
            const data = JSON.parse(message.data);
            const envelope: Envelope | undefined = data?.envelope;
            if (data?.type !== 'event' || !envelope || cancelled) return;
            setScenes((current) => [envelope, ...current].slice(0, 16));
            const target = envelope?.body?.target_avatar || envelope?.body?.agent_id;
            if (target) {
              setSpeaker(target);
              window.setTimeout(() => setSpeaker(null), 3500);
            }
            void refreshAgents();
          } catch {
            // Malformed realtime event: ignore. Never synthesize operational state.
          }
        };
      } catch {
        setBackendUp(false);
      }
    }

    return () => {
      cancelled = true;
      window.clearInterval(poll);
      ws?.close();
    };
  }, []);

  const activeError = error || (mode === 'agents' ? worldError : mode === 'portfolio' ? portfolioError : councilError);

  return (
    <div className="min-h-screen bg-[#080808] text-stone-100">
      <header className="flex flex-wrap items-center justify-between gap-5 border-b border-white/10 px-6 py-5 lg:px-8">
        <div className="flex items-center gap-4">
          <Link href="/" className="border border-white/10 p-2 text-stone-500 hover:text-white" aria-label="Back to Mission Control">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="text-[10px] uppercase tracking-[0.34em] text-amber-100/60">Owner observation cockpit</div>
            <h1 className="mt-1 text-xl font-semibold">Pauli&apos;s World</h1>
            <p className="mt-0.5 text-xs text-stone-500">Portfolio topology, council dissent, operational agents, evidence and gates. No fabricated activity.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex border border-white/10 p-1 text-[10px] uppercase tracking-wider">
            <button onClick={() => setMode('portfolio')} className={`px-3 py-1.5 ${mode === 'portfolio' ? 'bg-white text-black' : 'text-stone-500'}`}>Portfolio</button>
            <button onClick={() => setMode('council')} className={`px-3 py-1.5 ${mode === 'council' ? 'bg-white text-black' : 'text-stone-500'}`}>Council</button>
            <button onClick={() => setMode('agents')} className={`px-3 py-1.5 ${mode === 'agents' ? 'bg-white text-black' : 'text-stone-500'}`}>Agent room</button>
          </div>
          <span className={`flex items-center gap-2 border px-3 py-2 text-[10px] uppercase tracking-wider ${backendUp ? 'border-emerald-400/20 text-emerald-300' : 'border-red-400/20 text-red-300'}`}>
            {backendUp ? <Radio className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
            Agent backend {backendUp ? 'live' : 'offline'}
          </span>
          <button
            onClick={listening ? stop : start}
            disabled={backendUp !== true}
            className="border border-white/10 bg-stone-100 px-4 py-2 text-xs font-semibold text-black disabled:cursor-not-allowed disabled:opacity-30"
          >
            {listening ? 'Listening…' : 'Talk to Hermes'}
          </button>
        </div>
      </header>

      {activeError && (
        <div className="border-b border-red-400/20 bg-red-950/10 px-8 py-3 text-xs text-red-200">
          {activeError}
        </div>
      )}

      {mode === 'portfolio' && (
        <main className="px-6 py-6 lg:px-8">
          {portfolio ? (
            <>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3 text-[10px] uppercase tracking-wider text-stone-600">
                <span>Source: {portfolio.source}</span>
                <span>Snapshot: {portfolio.generated_at}</span>
              </div>
              <CommandWorld snapshot={portfolio} />
            </>
          ) : (
            <div className="grid min-h-[520px] place-items-center border border-white/10 text-sm text-stone-600">
              Loading authoritative portfolio graph…
            </div>
          )}
        </main>
      )}

      {mode === 'council' && (
        <main className="px-6 py-6 lg:px-8">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-[0.28em] text-amber-100/60">Evidence, not theater</div>
              <h2 className="mt-2 text-lg font-semibold">Portfolio Council</h2>
              <p className="mt-1 text-xs text-stone-500">Seven independent perspectives and Hermes synthesis. This surface is read-only; it cannot manufacture approvals or spend.</p>
            </div>
            <div className="text-[10px] uppercase tracking-wider text-stone-600">{decisions.length} persisted decisions</div>
          </div>
          <CouncilChamber decisions={decisions} />
        </main>
      )}

      {mode === 'agents' && (
        <main className="grid gap-6 px-6 py-6 lg:grid-cols-[1fr_360px] lg:px-8">
          <section className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 text-[10px] uppercase tracking-wider text-stone-600">
              <span>Source: {state.source || 'unknown'}</span>
              <span>{state.generated_at || ''}</span>
            </div>
            <ThreeScene avatars={state.avatars} speakingAvatarId={speaker} sceneCue={state.schedule_cue} />
            {transcript && (
              <div className="border border-white/10 bg-[#0e0e0e] px-4 py-3 text-sm">
                <span className="text-stone-500">You said: </span>{transcript}
              </div>
            )}
            {lastResponse?.halt && (
              <div className="border border-red-400/20 bg-red-950/10 px-4 py-3 text-sm text-red-200">
                Guardian halted this request: {lastResponse?.body?.reason || 'policy or safety boundary'}
              </div>
            )}
          </section>

          <aside>
            <div className="border border-white/10 bg-[#0e0e0e] p-5">
              <div className="text-[10px] uppercase tracking-[0.28em] text-stone-500">Verified event feed</div>
              <ul className="mt-4 max-h-[640px] space-y-2 overflow-y-auto text-xs">
                {scenes.length === 0 && (
                  <li className="border border-white/10 p-4 text-stone-600">No persisted world events have been received.</li>
                )}
                {scenes.map((scene) => (
                  <li key={`${scene.event_id}-${scene.ts}`} className="border border-white/10 bg-black/20 p-3">
                    <div className="font-mono text-[10px] uppercase tracking-wider text-amber-100/60">{scene.route} · {scene.stage}</div>
                    <div className="mt-2 leading-5 text-stone-300">
                      {scene.body?.response_text || scene.body?.public_summary || scene.body?.lounge_scene_intent || JSON.stringify(scene.body).slice(0, 160)}
                    </div>
                    <div className="mt-2 text-[10px] text-stone-600">{scene.ts}</div>
                  </li>
                ))}
              </ul>
            </div>
          </aside>
        </main>
      )}
    </div>
  );
}
