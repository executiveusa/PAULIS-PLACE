'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowLeft, Radio, WifiOff } from 'lucide-react';
import { council as councilApi, lounge as loungeApi, Envelope, LoungeState, PortfolioDecision, AVATAR_ROSTER } from '@/lib/loungeApi';
import { fetchPauliverseSnapshot, PauliverseSnapshot } from '@/lib/pauliverseApi';
import { useVoiceCommand } from './useVoiceCommand';

const ThreeScene = dynamic(() => import('./ThreeScene'), { ssr: false });
const CommandWorld = dynamic(() => import('./CommandWorld'), { ssr: false });
const CouncilChamber = dynamic(() => import('./CouncilChamber'), { ssr: false });

const POSITIONS: Array<[number, number, number]> = [
  [0, 0, 0], [-3.8, 0, -1.5], [3.8, 0, -1.5], [-5.4, 0, 2.2],
  [5.4, 0, 2.2], [-2.7, 0, 4.2], [2.7, 0, 4.2], [0, 0, 5.3],
];

const EMPTY_STATE: LoungeState = {
  lounge: "Pauli's Place",
  setting: 'Operational world · live backend state only',
  avatars: AVATAR_ROSTER.map((agent, index) => ({
    id: agent.id,
    name: agent.name,
    position: POSITIONS[index] || [0, 0, 0],
    model: 'persistent-agent',
    state: 'offline',
  })),
  schedule_cue: 'Waiting for live world state',
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

  useEffect(() => {
    let cancelled = false;

    fetchPauliverseSnapshot().then((snapshot) => {
      if (cancelled) return;
      setPortfolio(snapshot);
      setPortfolioError('');
    }).catch((error) => {
      if (cancelled) return;
      setPortfolio(null);
      setPortfolioError(error instanceof Error ? error.message : 'Portfolio snapshot unavailable');
    });

    loungeApi.state().then((next) => {
      if (cancelled) return;
      setState(next);
      setBackendUp(true);
      setWorldError('');
    }).catch((error) => {
      if (cancelled) return;
      setBackendUp(false);
      setWorldError(error instanceof Error ? error.message : 'World backend unavailable');
      setState(EMPTY_STATE);
    });

    loungeApi.scenes(12).then((result) => {
      if (!cancelled) setScenes(result.scenes);
    }).catch(() => {
      if (!cancelled) setScenes([]);
    });

    councilApi.portfolioDeliberations(12).then((result) => {
      if (cancelled) return;
      setDecisions(result.deliberations);
      setCouncilError('');
    }).catch((error) => {
      if (cancelled) return;
      setDecisions([]);
      setCouncilError(error instanceof Error ? error.message : 'Council evidence unavailable');
    });

    const configured = process.env.NEXT_PUBLIC_LOUNGE_WS_URL;
    let ws: WebSocket | null = null;
    if (configured) {
      try {
        ws = new WebSocket(configured);
        ws.onopen = () => setBackendUp(true);
        ws.onerror = () => setBackendUp(false);
        ws.onmessage = (message) => {
          try {
            const data = JSON.parse(message.data);
            const envelope: Envelope | undefined = data?.envelope;
            if (data?.type !== 'event' || !envelope) return;
            setScenes((current) => [envelope, ...current].slice(0, 12));
            const target = envelope?.body?.target_avatar;
            if (target) {
              setSpeaker(target);
              window.setTimeout(() => setSpeaker(null), 3500);
            }
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
      ws?.close();
    };
  }, []);

  const onAccept = (env: Envelope) => {
    setScenes((current) => [env, ...current].slice(0, 12));
    const target = env?.body?.target_avatar;
    if (target) {
      setSpeaker(target);
      window.setTimeout(() => setSpeaker(null), 3500);
    }
  };

  const { listening, transcript, error, lastResponse, start, stop } = useVoiceCommand({ onAccept });
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
            <h1 className="mt-1 text-xl font-semibold">Pauli's World</h1>
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
                  <li className="border border-white/10 p-4 text-stone-600">No verified world events have been received.</li>
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
