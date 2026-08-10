'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowLeft, Radio, WifiOff } from 'lucide-react';
import { lounge as loungeApi, Envelope, LoungeState, AVATAR_ROSTER } from '@/lib/loungeApi';
import { useVoiceCommand } from './useVoiceCommand';

const ThreeScene = dynamic(() => import('./ThreeScene'), { ssr: false });

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

export default function LoungeClient() {
  const [state, setState] = useState<LoungeState>(EMPTY_STATE);
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [scenes, setScenes] = useState<Envelope[]>([]);
  const [speaker, setSpeaker] = useState<string | null>(null);
  const [worldError, setWorldError] = useState('');

  useEffect(() => {
    let cancelled = false;
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

    loungeApi.scenes(12).then((result) => setScenes(result.scenes)).catch(() => setScenes([]));

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
            // malformed realtime event: ignore, never synthesize state
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

  return (
    <div className="min-h-screen bg-[#080808] text-stone-100">
      <header className="flex items-center justify-between gap-5 border-b border-white/10 px-6 py-5 lg:px-8">
        <div className="flex items-center gap-4">
          <Link href="/" className="border border-white/10 p-2 text-stone-500 hover:text-white" aria-label="Back to Mission Control">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="text-[10px] uppercase tracking-[0.34em] text-amber-100/60">Observable world</div>
            <h1 className="mt-1 text-xl font-semibold">Pauli's World</h1>
            <p className="mt-0.5 text-xs text-stone-500">Avatars mirror operational agent state. No synthetic activity.</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`flex items-center gap-2 border px-3 py-2 text-[10px] uppercase tracking-wider ${backendUp ? 'border-emerald-400/20 text-emerald-300' : 'border-red-400/20 text-red-300'}`}>
            {backendUp ? <Radio className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
            {backendUp ? 'Live' : 'Backend offline'}
          </span>
          <button
            onClick={listening ? stop : start}
            disabled={backendUp === false}
            className="border border-white/10 bg-stone-100 px-4 py-2 text-xs font-semibold text-black disabled:cursor-not-allowed disabled:opacity-30"
          >
            {listening ? 'Listening…' : 'Talk to the room'}
          </button>
        </div>
      </header>

      {(error || worldError) && (
        <div className="border-b border-red-400/20 bg-red-950/10 px-8 py-3 text-xs text-red-200">
          {error || worldError}
        </div>
      )}

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
            <div className="text-[10px] uppercase tracking-[0.28em] text-stone-500">Live event feed</div>
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
    </div>
  );
}
